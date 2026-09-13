import cv2
import numpy as np
from dataclasses import dataclass, field
from math import hypot

# ============================================================
# visitor_counter.py
#
# AI 모델 없이 OpenCV 움직임 감지만으로 방문객 입장/퇴장 감지
# 화면 기준: 왼쪽 = 입구, 가운데 = 복도, 오른쪽 = 가게
# ============================================================


# ------------------------------------------------------------
# [1] 사용자가 쉽게 수정할 수 있는 설정값
# ------------------------------------------------------------

# 노트북 기본 카메라는 보통 0번입니다.
# 외장 카메라를 쓰는 경우 1, 2로 바꿔보세요.
CAMERA_INDEX = 0

# 처리할 영상 크기입니다.
# 카메라가 다른 해상도를 지원하더라도 프로그램 내부에서는 이 크기로 맞춥니다.
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 기준선 위치 비율입니다.
# 0.35는 화면 왼쪽에서 35% 위치, 0.65는 65% 위치를 의미합니다.
LEFT_LINE_RATIO = 0.35
RIGHT_LINE_RATIO = 0.65

# 관심 영역 ROI 설정입니다.
# 화면 전체가 아니라 중앙~하단부만 움직임 감지에 사용합니다.
# 천장, 조명, 먼 배경 움직임을 줄이는 데 도움이 됩니다.
ROI_TOP_RATIO = 0.30       # 화면 높이의 30% 지점부터
ROI_BOTTOM_RATIO = 0.95    # 화면 높이의 95% 지점까지

# 너무 작은 움직임을 무시하기 위한 최소 contour 면적입니다.
# 사람이 작게 잡히면 값을 낮추고, 노이즈가 많이 잡히면 값을 높이세요.
MIN_CONTOUR_AREA = 1800

# 사람 후보 bounding box의 최소 크기입니다.
# 작은 그림자, 손 흔들림, 조명 변화 등을 줄이는 용도입니다.
MIN_BOX_WIDTH = 25
MIN_BOX_HEIGHT = 45

# BackgroundSubtractorMOG2 설정입니다.
# HISTORY가 클수록 배경 변화에 천천히 적응합니다.
# VAR_THRESHOLD가 클수록 둔감해지고, 작을수록 민감해집니다.
MOG_HISTORY = 300
MOG_VAR_THRESHOLD = 40
MOG_DETECT_SHADOWS = True

# 그림자 제거용 threshold입니다.
# MOG2에서 그림자는 보통 회색값 127 근처로 나오므로 200 이상만 움직임으로 봅니다.
MASK_THRESHOLD = 200

# morphology 노이즈 제거 설정입니다.
MORPH_KERNEL_SIZE = 5
MORPH_OPEN_ITERATIONS = 1
MORPH_CLOSE_ITERATIONS = 2
DILATE_ITERATIONS = 2

# 추적 설정입니다.
# MAX_TRACK_DISTANCE: 이전 중심점과 새 중심점이 이 거리 이내면 같은 물체로 판단합니다.
MAX_TRACK_DISTANCE = 80
MAX_MISSED_FRAMES = 12

# 기준선 근처에서 흔들릴 때 중복 카운트를 막는 전역 cooldown입니다.
# 값이 클수록 중복 카운트는 줄지만, 여러 사람이 빠르게 지나갈 때 일부를 놓칠 수 있습니다.
GLOBAL_COUNT_COOLDOWN_FRAMES = 35

# 프로그램 시작 또는 배경 초기화 후 배경을 학습하는 프레임 수입니다.
# 이 시간에는 카운트하지 않습니다. 시작 직후 카메라 앞이 비어 있으면 더 좋습니다.
WARMUP_FRAMES = 30

# ENTER / EXIT 표시를 화면에 유지할 프레임 수입니다.
STATUS_HOLD_FRAMES = 35

WINDOW_NAME = "OpenCV Visitor Counter"


# ------------------------------------------------------------
# [2] 추적 대상 정보를 저장하는 클래스
# ------------------------------------------------------------

@dataclass
class Track:
    track_id: int
    cx: int
    cy: int
    bbox: tuple
    last_seen_frame: int
    previous_cx: int | None = None
    previous_cy: int | None = None
    missed_frames: int = 0
    crossed_order: list = field(default_factory=list)  # 예: ["left", "right"]
    counted: bool = False

    def update(self, cx: int, cy: int, bbox: tuple, frame_index: int):
        """같은 물체로 매칭된 새 위치를 저장합니다."""
        self.previous_cx = self.cx
        self.previous_cy = self.cy
        self.cx = cx
        self.cy = cy
        self.bbox = bbox
        self.last_seen_frame = frame_index
        self.missed_frames = 0


# ------------------------------------------------------------
# [3] OpenCV 처리 함수들
# ------------------------------------------------------------

def create_background_subtractor():
    """배경 제거 객체를 새로 만듭니다. c 키를 누를 때도 이 함수로 초기화합니다."""
    return cv2.createBackgroundSubtractorMOG2(
        history=MOG_HISTORY,
        varThreshold=MOG_VAR_THRESHOLD,
        detectShadows=MOG_DETECT_SHADOWS,
    )


def preprocess_roi(frame, roi_top, roi_bottom):
    """ROI 부분만 잘라 grayscale + blur 처리를 합니다."""
    roi = frame[roi_top:roi_bottom, :]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return blurred


def detect_motion(frame, bg_subtractor, roi_top, roi_bottom):
    """움직임 영역을 찾아 bounding box, 중심점 정보를 반환합니다."""
    blurred_roi = preprocess_roi(frame, roi_top, roi_bottom)

    # 배경 제거 적용
    fg_mask = bg_subtractor.apply(blurred_roi)

    # 그림자와 약한 변화 제거
    _, binary = cv2.threshold(fg_mask, MASK_THRESHOLD, 255, cv2.THRESH_BINARY)

    # morphology 연산으로 작은 노이즈 제거 및 끊어진 영역 연결
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE),
    )
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=MORPH_OPEN_ITERATIONS)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=MORPH_CLOSE_ITERATIONS)
    binary = cv2.dilate(binary, kernel, iterations=DILATE_ITERATIONS)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < MIN_CONTOUR_AREA:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        if w < MIN_BOX_WIDTH or h < MIN_BOX_HEIGHT:
            continue

        # ROI 내부 좌표를 전체 화면 좌표로 변환합니다.
        full_y = y + roi_top
        cx = x + w // 2
        cy = full_y + h // 2

        detections.append({
            "bbox": (x, full_y, w, h),
            "cx": cx,
            "cy": cy,
            "area": area,
        })

    # 큰 물체부터 처리하면 매칭이 조금 더 안정적입니다.
    detections.sort(key=lambda d: d["area"], reverse=True)

    return detections, binary


def update_tracks(tracks, detections, next_track_id, frame_index):
    """현재 감지 결과를 기존 추적 대상과 연결합니다."""
    matched_track_ids = set()

    for det in detections:
        cx = det["cx"]
        cy = det["cy"]
        bbox = det["bbox"]

        best_track = None
        best_distance = float("inf")

        for track in tracks:
            if track.track_id in matched_track_ids:
                continue

            distance = hypot(cx - track.cx, cy - track.cy)

            if distance < best_distance:
                best_distance = distance
                best_track = track

        if best_track is not None and best_distance <= MAX_TRACK_DISTANCE:
            best_track.update(cx, cy, bbox, frame_index)
            matched_track_ids.add(best_track.track_id)
        else:
            # 새 물체로 등록합니다.
            new_track = Track(
                track_id=next_track_id,
                cx=cx,
                cy=cy,
                bbox=bbox,
                last_seen_frame=frame_index,
            )
            tracks.append(new_track)
            matched_track_ids.add(next_track_id)
            next_track_id += 1

    # 이번 프레임에서 보이지 않은 track은 missed_frames를 증가시킵니다.
    for track in tracks:
        if track.track_id not in matched_track_ids:
            track.missed_frames += 1

    # 너무 오래 안 보인 track은 삭제합니다.
    tracks = [t for t in tracks if t.missed_frames <= MAX_MISSED_FRAMES]

    return tracks, next_track_id


def add_crossing(track, line_name):
    """기준선 통과 순서를 저장합니다. 같은 선 반복 통과는 무시합니다."""
    if track.counted:
        return

    if not track.crossed_order:
        track.crossed_order.append(line_name)
    elif track.crossed_order[-1] != line_name and len(track.crossed_order) < 2:
        track.crossed_order.append(line_name)


def process_crossings(tracks, frame_index, left_line_x, right_line_x, last_count_frame):
    """기준선 통과 순서를 보고 입장/퇴장을 판정합니다."""
    enter_delta = 0
    exit_delta = 0
    new_status = None

    for track in tracks:
        # 이번 프레임에 실제로 감지된 track만 처리합니다.
        if track.last_seen_frame != frame_index:
            continue

        # 새로 생긴 track은 이전 위치가 없으므로 통과 여부를 판단할 수 없습니다.
        if track.previous_cx is None:
            continue

        if track.counted:
            continue

        prev_x = track.previous_cx
        curr_x = track.cx

        # 왼쪽 -> 오른쪽 이동 중 통과한 선을 순서대로 기록합니다.
        if curr_x > prev_x:
            if prev_x < left_line_x <= curr_x:
                add_crossing(track, "left")
            if prev_x < right_line_x <= curr_x:
                add_crossing(track, "right")

        # 오른쪽 -> 왼쪽 이동 중 통과한 선을 순서대로 기록합니다.
        elif curr_x < prev_x:
            if prev_x > right_line_x >= curr_x:
                add_crossing(track, "right")
            if prev_x > left_line_x >= curr_x:
                add_crossing(track, "left")

        # 두 선을 모두 통과했는지 확인합니다.
        if len(track.crossed_order) >= 2:
            enough_cooldown = (frame_index - last_count_frame) >= GLOBAL_COUNT_COOLDOWN_FRAMES

            if track.crossed_order == ["left", "right"]:
                if enough_cooldown:
                    enter_delta += 1
                    last_count_frame = frame_index
                    new_status = "ENTER"

                track.counted = True

            elif track.crossed_order == ["right", "left"]:
                if enough_cooldown:
                    exit_delta += 1
                    last_count_frame = frame_index
                    new_status = "EXIT"

                track.counted = True

            else:
                # 예상 밖 순서라면 다시 시작합니다.
                track.crossed_order.clear()

    return enter_delta, exit_delta, new_status, last_count_frame


def get_track_state_text(track):
    """track별 기준선 통과 상태를 간단한 텍스트로 만듭니다."""
    if track.counted:
        return "counted"

    if track.crossed_order == ["left"]:
        return "left first"

    if track.crossed_order == ["right"]:
        return "right first"

    return "tracking"


def draw_overlay(
    frame,
    tracks,
    frame_index,
    enter_count,
    exit_count,
    status_text,
    left_line_x,
    right_line_x,
    roi_top,
    roi_bottom,
    paused=False,
):
    """화면에 기준선, bounding box, 중심점, 카운트 정보를 그립니다."""
    display = frame.copy()

    # ROI 영역 표시
    cv2.rectangle(display, (0, roi_top), (FRAME_WIDTH - 1, roi_bottom), (80, 80, 80), 1)
    cv2.putText(
        display,
        "ROI",
        (10, roi_top - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (180, 180, 180),
        1,
    )

    # 기준선 2개 표시
    cv2.line(display, (left_line_x, roi_top), (left_line_x, roi_bottom), (255, 0, 0), 2)
    cv2.line(display, (right_line_x, roi_top), (right_line_x, roi_bottom), (0, 0, 255), 2)

    cv2.putText(
        display,
        "LEFT LINE",
        (left_line_x - 70, roi_top + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 0, 0),
        2,
    )
    cv2.putText(
        display,
        "RIGHT LINE",
        (right_line_x - 75, roi_top + 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 255),
        2,
    )

    # 움직이는 물체 bounding box와 중심점 표시
    for track in tracks:
        if track.last_seen_frame != frame_index:
            continue

        x, y, w, h = track.bbox
        state = get_track_state_text(track)

        cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(display, (track.cx, track.cy), 5, (0, 255, 255), -1)

        cv2.putText(
            display,
            f"ID {track.track_id}: {state}",
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )

    # 상단 정보 표시용 배경 박스
    cv2.rectangle(display, (0, 0), (FRAME_WIDTH, 92), (0, 0, 0), -1)

    cv2.putText(
        display,
        f"ENTER: {enter_count}",
        (15, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 255, 0),
        2,
    )
    cv2.putText(
        display,
        f"EXIT : {exit_count}",
        (15, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (0, 200, 255),
        2,
    )
    cv2.putText(
        display,
        f"STATUS: {status_text}",
        (210, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        display,
        "q: quit | r: reset | p: pause | c: clear background",
        (210, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (220, 220, 220),
        1,
    )

    if paused:
        cv2.putText(
            display,
            "PAUSED",
            (FRAME_WIDTH // 2 - 75, FRAME_HEIGHT // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 255),
            3,
        )

    return display


# ------------------------------------------------------------
# [4] 메인 실행부
# ------------------------------------------------------------

def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("ERROR: 카메라를 열 수 없습니다. CAMERA_INDEX 값을 0, 1, 2로 바꿔보세요.")
        return

    # 카메라에 원하는 해상도를 요청합니다.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    # 실제로 프레임을 읽을 수 있는지 확인합니다.
    ret, test_frame = cap.read()

    if not ret or test_frame is None:
        print("ERROR: 카메라에서 프레임을 읽을 수 없습니다. 다른 프로그램이 카메라를 사용 중인지 확인하세요.")
        cap.release()
        return

    left_line_x = int(FRAME_WIDTH * LEFT_LINE_RATIO)
    right_line_x = int(FRAME_WIDTH * RIGHT_LINE_RATIO)
    roi_top = int(FRAME_HEIGHT * ROI_TOP_RATIO)
    roi_bottom = int(FRAME_HEIGHT * ROI_BOTTOM_RATIO)

    bg_subtractor = create_background_subtractor()

    tracks = []
    next_track_id = 1

    enter_count = 0
    exit_count = 0

    frame_index = 0
    last_count_frame = -GLOBAL_COUNT_COOLDOWN_FRAMES

    paused = False
    last_display = None

    status_message = "READY"
    status_until_frame = 0
    warmup_until_frame = WARMUP_FRAMES

    print("프로그램 시작")
    print("키 안내: q=종료, r=카운트 초기화, p=일시정지/재개, c=배경 모델 초기화")

    while True:
        if not paused:
            ret, frame = cap.read()

            if not ret or frame is None:
                print("ERROR: 카메라 프레임 수신에 실패했습니다. 프로그램을 종료합니다.")
                break

            # 처리 크기를 640x480으로 고정합니다.
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            frame_index += 1

            detections, _ = detect_motion(frame, bg_subtractor, roi_top, roi_bottom)

            # 시작 직후 또는 배경 초기화 직후에는 배경 학습만 하고 카운트하지 않습니다.
            if frame_index <= warmup_until_frame:
                tracks.clear()
                detections = []
                remaining = warmup_until_frame - frame_index + 1
                current_status = f"LEARNING BACKGROUND ({remaining})"

            else:
                tracks, next_track_id = update_tracks(
                    tracks,
                    detections,
                    next_track_id,
                    frame_index,
                )

                enter_delta, exit_delta, event_status, last_count_frame = process_crossings(
                    tracks,
                    frame_index,
                    left_line_x,
                    right_line_x,
                    last_count_frame,
                )

                if enter_delta > 0:
                    enter_count += enter_delta
                    print(f"ENTER detected, total enter count = {enter_count}")
                    status_message = "ENTER detected"
                    status_until_frame = frame_index + STATUS_HOLD_FRAMES

                if exit_delta > 0:
                    exit_count += exit_delta
                    print(f"EXIT detected, total exit count = {exit_count}")
                    status_message = "EXIT detected"
                    status_until_frame = frame_index + STATUS_HOLD_FRAMES

                # 현재 상태 표시
                if frame_index <= status_until_frame:
                    current_status = status_message

                elif len(detections) > 0:
                    # 첫 번째로 통과한 기준선이 있으면 그 상태를 보여줍니다.
                    active_states = [
                        get_track_state_text(t)
                        for t in tracks
                        if t.last_seen_frame == frame_index
                    ]

                    if "left first" in active_states:
                        current_status = "LEFT LINE crossed first"
                    elif "right first" in active_states:
                        current_status = "RIGHT LINE crossed first"
                    else:
                        current_status = "MOTION DETECTED"

                else:
                    current_status = "READY"

            display = draw_overlay(
                frame=frame,
                tracks=tracks,
                frame_index=frame_index,
                enter_count=enter_count,
                exit_count=exit_count,
                status_text=current_status,
                left_line_x=left_line_x,
                right_line_x=right_line_x,
                roi_top=roi_top,
                roi_bottom=roi_bottom,
                paused=False,
            )

            last_display = display
            cv2.imshow(WINDOW_NAME, display)

        else:
            # 일시정지 중에는 마지막 화면을 그대로 보여줍니다.
            if last_display is not None:
                paused_display = last_display.copy()

                paused_display = draw_overlay(
                    frame=paused_display,
                    tracks=[],
                    frame_index=frame_index,
                    enter_count=enter_count,
                    exit_count=exit_count,
                    status_text="PAUSED",
                    left_line_x=left_line_x,
                    right_line_x=right_line_x,
                    roi_top=roi_top,
                    roi_bottom=roi_bottom,
                    paused=True,
                )

                cv2.imshow(WINDOW_NAME, paused_display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("프로그램 종료")
            break

        elif key == ord("r"):
            enter_count = 0
            exit_count = 0
            tracks.clear()
            next_track_id = 1
            last_count_frame = -GLOBAL_COUNT_COOLDOWN_FRAMES
            status_message = "COUNTS RESET"
            status_until_frame = frame_index + STATUS_HOLD_FRAMES
            print("카운트를 초기화했습니다.")

        elif key == ord("p"):
            paused = not paused

            if paused:
                print("일시정지")
            else:
                print("재개")

        elif key == ord("c"):
            bg_subtractor = create_background_subtractor()
            tracks.clear()
            next_track_id = 1
            warmup_until_frame = frame_index + WARMUP_FRAMES
            status_message = "BACKGROUND RESET"
            status_until_frame = frame_index + STATUS_HOLD_FRAMES
            print("배경 모델을 초기화했습니다. 잠시 동안 배경을 다시 학습합니다.")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램이 종료되었습니다.")
        cv2.destroyAllWindows()