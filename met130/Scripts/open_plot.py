from PIL import Image

Input = input(">> Input the map you would like to recall in the format 'YYYY, MM, DD, HH, [area code], [level], [dpi], [assignment status]: ")
Input = Input.split(', ')
timestampNum = f"{Input[0]}-{Input[1]}-{Input[2]}-{Input[3]}Z"
daystamp = f"{Input[0]}-{Input[1]}-{Input[2]}"
area = Input[4]
level = Input[5]
dpiSet = Input[6]
assigned =  Input[7]

if assigned == 'y':
    saveLocale = 'Assignment Maps'
else:
    saveLocale = 'Test Maps'

save = Image.open(f'/home/sbailey4/Documents/met130/Maps/{saveLocale}/{daystamp}/{timestampNum}, {area} {level} Map, {dpiSet} DPI - Bailey, Sam.png')
save.show()