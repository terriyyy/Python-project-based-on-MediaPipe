
#!/usr/bin/python
#coding=utf-8
import random 
import time
    
def main(pos):
    index=1000
    while index>0:
        index-=1
        x=random.randint(0,600)
        y=random.randint(0,400)
        pos[0]=[x,y]
        time.sleep(0.03)
        print('subprocess',x,y)

if __name__ == '__main__':
    main()