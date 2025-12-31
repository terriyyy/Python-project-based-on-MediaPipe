from multiprocessing import Process, Pipe, Manager
import game
import cv
import test

if __name__ == '__main__':
    mgr = Manager()
    pos = mgr.list()
    pos.append([300,200])
    p1 = Process(target=test.main, args=(pos,))
    # p1 = Process(target=cv.main, args=(pos,))
    p2 = Process(target=game.main, args=(pos,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()