import os, AppOpener
# os.system(r"C:\Users\Yusuf\Desktop\Paint.lnk")
ap = ''
apps = AppOpener.give_appnames()
for app in apps: ap += app
print(ap)
print('\n'*10)
print(True if 'camera' in ap else False)