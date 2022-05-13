from pynput import keyboard
import numpy as np
import random

class play():
    def __init__(self):
        self.mat =  np.zeros((4,4))
        self.add_two()
        self.add_two()
        print("start")
        print(self.mat)
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()  
        listener.join() 

    def add_two(self):
        column_produce = random.randint(0,3)
        row_produce = random.randint(0,3)
        if self.mat[row_produce][column_produce]!=0:
            column_produce = random.randint(0,3)
            row_produce = random.randint(0,3)
        self.mat[row_produce][column_produce] = 2

    def up_key(self):
        for k in range(3):
            for col in range(4):
                for row in range(3):
                    if self.mat[row][col]==0 and self.mat[row+1][col]!=0:
                        self.mat[row][col],self.mat[row+1][col] = self.mat[row+1][col],self.mat[row][col]
        for col in range(4):
            for row in range(3):
                if self.mat[row][col] == self.mat[row+1][col]:
                    self.mat[row][col] = self.mat[row][col]*2
                    self.mat[row+1][col] = 0
        for k in range(3):
            for col in range(4):
                for row in range(3):
                    if self.mat[row][col]==0 and self.mat[row+1][col]!=0:
                        self.mat[row][col],self.mat[row+1][col] = self.mat[row+1][col],self.mat[row][col]

    def down_key(self):
        for k in range(3):
            for col in range(4):
                for row in range(3,0,-1):
                    if self.mat[row][col]==0 and self.mat[row-1][col]!=0:
                        self.mat[row][col],self.mat[row-1][col] = self.mat[row-1][col],self.mat[row][col]
        for col in range(4):
            for row in range(3,0,-1):
                if self.mat[row][col] == self.mat[row-1][col]:
                    self.mat[row][col] = self.mat[row][col]*2
                    self.mat[row-1][col] = 0
        for k in range(3):
            for col in range(4):
                for row in range(3,0,-1):
                    if self.mat[row][col]==0 and self.mat[row-1][col]!=0:
                        self.mat[row][col],self.mat[row-1][col] = self.mat[row-1][col],self.mat[row][col]

    def left_key(self):
        for k in range(3):
            for row in range(4):
                for col in range(3):
                    if self.mat[row][col]==0 and self.mat[row][col+1]!=0:
                        self.mat[row][col],self.mat[row][col+1] = self.mat[row][col+1],self.mat[row][col]
        for row in range(4):
            for col in range(3):
                if self.mat[row][col] == self.mat[row][col+1]:
                    self.mat[row][col] = self.mat[row][col]*2
                    self.mat[row][col+1] = 0
        for k in range(3):
            for row in range(4):
                for col in range(3):
                    if self.mat[row][col]==0 and self.mat[row][col+1]!=0:
                        self.mat[row][col],self.mat[row][col+1] = self.mat[row][col+1],self.mat[row][col]

    def right_key(self):
        for k in range(3):
            for row in range(4):
                for col in range(3,0,-1):
                    if self.mat[row][col]==0 and self.mat[row][col-1]!=0:
                        self.mat[row][col],self.mat[row][col-1] = self.mat[row][col-1],self.mat[row][col]
        for row in range(4):
            for col in range(3,0,-1):
                if self.mat[row][col] == self.mat[row][col-1]:
                    self.mat[row][col] = self.mat[row][col]*2
                    self.mat[row][col-1] = 0
        for k in range(3):
            for row in range(4):
                for col in range(3,0,-1):
                    if self.mat[row][col]==0 and self.mat[row][col-1]!=0:
                        self.mat[row][col],self.mat[row][col-1] = self.mat[row][col-1],self.mat[row][col]

    def detect_2048(self):
        for row in range(4):
            for col in range(4):
                if self.mat[row][col] == 16:
                    return True
        return False
        
    def move_block(self,key):

        if key == 'up':
            self.up_key()
        elif key == 'down':
            self.down_key()
        elif key == 'left':
            self.left_key()
        elif key == 'right':
            self.right_key()

        if self.detect_2048():
            print("win")
            exit()

        self.add_two()
        print(self.mat)
        
        
    def on_press(self,key):
        if key == keyboard.Key.esc:
            return False  
        try:
            k = key.char  
        except:
            k = key.name  
        if k in ['up', 'down', 'left', 'right']: 
            print('Key pressed: ' + k)
            self.move_block(k)
            #return False  

if __name__ == '__main__':
    play()