from tkinter.constants import END
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

import tkinter
import tkinter.ttk as ttk
import tkinter.messagebox as msgbox
from tkinter import filedialog

import time
import os
import sys





main = tkinter.Tk()
main.title("Particle")
main.geometry("600x440+100+100")

main.resizable(False, False)



name_txt = tkinter.Entry(main, width=50)
name_txt.place(x = 10, y = 15)

name_txt.insert(END, "펑션팩 이름을 입력하세요.")


particle_txt1 = tkinter.Entry(main, width=50)
particle_txt1.place(x = 10, y = 40)

particle_txt1.insert(END, "사용할 파티클 이름을 입력하세요.")


# particle_txt = tkinter.Entry(main, width=50)
# particle_txt.place(x = 10, y = 60)

# particle_txt.insert(END, "사용할 파티클 이름을 입력하세요.")



def file_select():
    global image, image_bw, pix

    files = filedialog.askopenfilename(title = "이미지 파일을 선택하세요.", \
        filetypes = (("PNG 파일", "*.png"), ("JPG 파일", "*.jpg")), \
        initialdir = "C:/" )
    print(files)
    path = files

    image_pil = Image.open(path)
    image = np.array(image_pil)

    pix = np.array(image)

    print(image.shape)
    print(np.min(image), np.max(image))

    #크기
    print(image.size)

    #이미지 흑백으로 열기
    image_pil = Image.open(path).convert("L")
    image_bw = np.array(image_pil)

    #plt.show()
    

    # photo = tkinter.PhotoImage(file = files)
    
    if len(str(files)) < 40:
        label1 = tkinter.Label(main, text = str(files))
    elif len(str(files)) >= 40:
        label1 = tkinter.Label(main, text = str(files)[:40])
        label2 = tkinter.Label(main, text = str(files)[40:])

    label1.place(x = 10,y = 120)
    label2.place(x = 10,y = 140)

file_select_btn = tkinter.Button(main, text = "파일 선택", width=8, height=1, command = file_select)
file_select_btn.place(x = 10,y = 90)


color_mode_int = tkinter.IntVar()
color_mode = tkinter.Checkbutton(main, text = "색 모드", variable = color_mode_int)

color_mode.place(x = 10, y = 180)




labal1 = tkinter.Label(main, text ="----------------------------------")
labal1.place(x = 400,y = 1)


color_int = tkinter.IntVar()
mm1 = tkinter.Radiobutton(main, text = "색 부분 인식", value = 1, variable = color_int)
mm1.select()
mm2 = tkinter.Radiobutton(main, text = "검은 부분 인식", value = 2, variable = color_int)
mm3 = tkinter.Radiobutton(main, text = "모든 부분 인식", value = 3, variable = color_int)
mm1.place(x = 400,y = 20)
mm2.place(x = 400,y = 40)
mm3.place(x = 400,y = 60)



labal2 = tkinter.Label(main, text ="----------------------------------")
labal2.place(x = 400,y = 80)



rotate_int = tkinter.IntVar()
pp = tkinter.Radiobutton(main, text = "회전 적용 안함", value = 1, variable = rotate_int)
pp.select()
pp1 = tkinter.Radiobutton(main, text = "↺ 왼쪽으로 90도 돌리기", value = 2, variable = rotate_int)
pp2 = tkinter.Radiobutton(main, text = "↻ 오른쪽으로 90도 돌리기", value = 3, variable = rotate_int)
pp3 = tkinter.Radiobutton(main, text = "뒤집기", value = 4, variable = rotate_int)

pp.place(x = 400,y = 110)
pp1.place(x = 400,y = 130)
pp2.place(x = 400,y = 150)
pp3.place(x = 400,y = 170)



labal3 = tkinter.Label(main, text ="----------------------------------")
labal3.place(x = 400,y = 190)


rotation_values = ["front", "side", "bottom"]
rotation_box = ttk.Combobox(main, height=5, values=rotation_values, state = "readonly") 
rotation_box.place(x = 400,y = 230)
rotation_box.set("설정 방향")





width_txt = tkinter.Entry(main, width=25)
width_txt.place(x = 400,y = 255)

width_txt.insert(END, "가로 길이(기본값 : 3)")


distance_txt = tkinter.Entry(main, width=25)
distance_txt.place(x = 400,y = 280)

distance_txt.insert(END, "파티클간의 간격(기본값:0.2)")



p_var = tkinter.DoubleVar()
progressbar = ttk.Progressbar(main, maximum = 100, length = 150, variable = p_var)
progressbar.place(x = 410,y = 320)


def ok():
    global name, particle, rotation, image, color_mode_int

    name = name_txt.get()
    particle = particle_txt1.get()
    rotation = rotation_box.get()
    width = float(width_txt.get())
    rotate = rotate_int.get()
    
    

    color = color_int.get()

    n = float(distance_txt.get())

    if str(n) == "파티클간의 간격(기본값:0.2)":
        n = 0.2

    ratio = image.shape[0]/width
    n *= ratio

    draw = open("{0}.mcfunction".format(name), "w",  encoding = "utf8")

    
    

    num = 100 / ((image.shape[0] / n) * (image.shape[1] / n))
    plt.imshow(image_bw,'gray')
    i = 0
    


    
    if rotation == "front":

        print(rotate)

        for i_x in range(0, image.shape[0], int(n)):
            for i_y in range(0, image.shape[1], int(n)):
                
                if color_mode_int.get() == 1:
                    particle_temp = pix[i_x, i_y]
                    red = 1 + (particle_temp[0] - particle_temp[0]%17)
                    green = 1 + (particle_temp[1] - particle_temp[1]%17)
                    blue = 1 + (particle_temp[2] - particle_temp[2]%17)
                    
                    particle = "particle{0}.{1}.{2}".format(red, green, blue)


                if rotate == 1:    
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), -((-1 * (width/2)) + x)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), -((-1 * (width/2)) + x)), file = draw)
                    if color == 3:
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^{2}^".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), -((-1 * (width/2)) + x)), file = draw)

                
                if rotate == 2:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, (-1 * (width/2)) + x, (width * (image.shape[1]/image.shape[0]))/2 - y), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, (-1 * (width/2)) + x, (width * (image.shape[1]/image.shape[0]))/2 - y), file = draw)
                    if color == 3:
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^{2}^".format(particle, (-1 * (width/2)) + x, (width * (image.shape[1]/image.shape[0]))/2 - y), file = draw)
                    



                if rotate == 3:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, (-1 * (width/2)) + x, (width * (image.shape[1]/image.shape[0]))/2 - y), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, (-1 * (width/2)) + x, (width * (image.shape[1]/image.shape[0]))/2 - y), file = draw)
                    if color == 3:
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^{2}^".format(particle, (-1 * (width/2)) + x, (width * (image.shape[1]/image.shape[0]))/2 - y), file = draw)


                if rotate == 4:

                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), (-1 * (width/2)) + x), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^{2}^".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), (-1 * (width/2)) + x), file = draw)
                    if color == 3:
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^{2}^".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), (-1 * (width/2)) + x), file = draw)


                print(i_x, i_y, image_bw[i_x][i_y], i, color)
                i += num
                p_var.set(i)
                progressbar.update()
                
            print("", end = "\n", file = draw)



    

    if rotation == "side":


        print(rotate)


        

        for i_x in range(0, image.shape[0], int(n)):
            for i_y in range(0, image.shape[1], int(n)):

                if color_mode_int.get() == 1:
                    particle_temp = pix[i_x, i_y]
                    red = 1 + (particle_temp[0] - particle_temp[0]%17)
                    green = 1 + (particle_temp[1] - particle_temp[1]%17)
                    blue = 1 + (particle_temp[2] - particle_temp[2]%17)

                    particle = "particle{0}.{1}.{2}".format(red, green, blue)


                if rotate == 1:
                    print("normal")  
                
                    if color == 1:
                        if image_bw[i_x][i_y] > 10 and image_bw[i_x][i_y] < 250:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, -((-1 * (width/2)) + x), ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, -((-1 * (width/2)) + x), ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    if color == 3:
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^^{1}^{2}".format(particle, -((-1 * (width/2)) + x), ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    
                

                if rotate == 2:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 3:                            
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^^{1}^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)


                if rotate == 3:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 3:                
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^^{1}^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)                                


                if rotate == 4:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, (-1 * (width/2)) + x, ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^^{1}^{2}".format(particle, (-1 * (width/2)) + x, ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    if color == 3:                            
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^^{1}^{2}".format(particle, (-1 * (width/2)) + x, ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                                                
                        

                print(i_x, i_y, image_bw[i_x][i_y], i, color)
                i += num
                p_var.set(i)
                progressbar.update()

            print("", end = "\n", file = draw)

        



    if rotation == "bottom": 

        print(rotate)
        



    
        print("normal")

        for i_x in range(0, image.shape[0], int(n)):
            for i_y in range(0, image.shape[1], int(n)):
                
                
                if color_mode_int.get() == 1:
                    particle_temp = pix[i_x, i_y]
                    red = 1 + (particle_temp[0] - particle_temp[0]%17)
                    green = 1 + (particle_temp[1] - particle_temp[1]%17)
                    blue = 1 + (particle_temp[2] - particle_temp[2]%17)
                    
                    particle = "particle{0}.{1}.{2}".format(red, green, blue)
                    
                if rotate == 1:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), ((-1 * (width/2)) + x)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), ((-1 * (width/2)) + x)), file = draw)
                    if color == 3:                                
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^^{2}".format(particle, -((width * (image.shape[1]/image.shape[0]))/2 - y), ((-1 * (width/2)) + x)), file = draw)                                    
                


                if rotate == 2:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 3:                                
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^^{2}".format(particle, (width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)


                if rotate == 3:

                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, -(width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, -(width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)
                    if color == 3:                                
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^^{2}".format(particle, -(width * (image.shape[1]/image.shape[0]))/2 - y, -((-1 * (width/2)) + x)), file = draw)                                


                if rotate == 4:
                    if color == 1:
                        if image_bw[i_x][i_y] > 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, (-1 * (width/2)) + x, ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    if color == 2:
                        if image_bw[i_x][i_y] < 10:
                            x = i_x/ratio
                            y = i_y/ratio
                            print("particle {0} ^{1}^^{2}".format(particle, (-1 * (width/2)) + x, ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)
                    if color == 3:                                
                        x = i_x/ratio
                        y = i_y/ratio
                        print("particle {0} ^{1}^^{2}".format(particle, (-1 * (width/2)) + x, ((width * (image.shape[1]/image.shape[0]))/2 - y)), file = draw)                

            print(i_x, i_y, image_bw[i_x][i_y], i, color)
            i += num
            p_var.set(i)
            progressbar.update()

    print("", end = "\n", file = draw)


    msgbox.showinfo("알림", "완료되었습니다.")
    
    
    
    print("완료!")

    
    sys.exit()




    

ok_side = tkinter.Button(main, text = "확인", width=10, height=3, command = ok)
ok_side.place(x = 440,y = 350)




main.mainloop()





