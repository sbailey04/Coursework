from PIL import Image

Input = input(">> Input the map you would like to recall in the format 'YYYY, MM, DD, HH, [area code], [level], [dpi], [assignment status], [contour?], [dTime]: ")
Input = Input.split(', ')
timestampNum = f"{Input[0]}-{Input[1]}-{Input[2]}-{Input[3]}Z"
daystamp = f"{Input[0]}-{Input[1]}-{Input[2]}"
area = Input[4]
level = Input[5]
dpiSet = Input[6]
assigned =  Input[7]
contour = Input[8]
dTime = f"{Input[9]}H"

if assigned == 'y':
    saveLocale = 'Assignment_Maps'
else:
    saveLocale = 'Test_Maps'

if contour == 'y':
    save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {dTime}, {area} {level} Contour Map, {dpiSet} DPI - Bailey, Sam.png')
else:
    save = Image.open(f'../Maps/{saveLocale}/{daystamp}/{timestampNum}, {area} {level} Map, {dpiSet} DPI - Bailey, Sam.png')
save.show()