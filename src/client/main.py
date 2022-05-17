import asyncio
from websockets.client import connect, WebSocketClientProtocol
from messages import *
from shared_utils import receive_events, next_event, send_event
import logging
import os
import random
import numpy as np
import glfw
import time
import OpenGL.GL as gl
import freetype

ROOM_ID_LENGTH = 8;

Font_Game   = 0;
Font_UI     = 1;
Font_OnePastLast = 2;

Key_Up          = 1;
Key_Down        = 2;
Key_Left        = 3;
Key_Right       = 4;
Key_Backspace   = 5;
Key_Escape      = 6;
Key_Enter       = 7;
Key_Space       = 8;
Mouse_Left      = 9;
Mouse_Right     = 10;
Mouse_Middle    = 11;
Key_0           = 12;
Key_1           = 13;
Key_2           = 14;
Key_3           = 15;
Key_4           = 16;
Key_5           = 17;
Key_6           = 18;
Key_7           = 19;
Key_8           = 20;
Key_9           = 21;

Key_Dev2        = 22;
Key_Dev4        = 23;
Key_Dev6        = 24;
Key_Dev8        = 25;
Key_DevPlus     = 26;
Key_DevMinus    = 27;
Button_OnePastLast = 28;

Mode_Game   = 0;
Mode_Menu   = 1;

UIID_None       = 0;
UIID_Back       = 1;
UIID_CreateRoom = 2;
UIID_JoinRoom   = 3;
UIID_Exit       = 4;

class v4:
    def __init__(self, R: float, G: float, B: float, A: float):
        self.R = R;
        self.G = G;
        self.B = B;
        self.A = A;

class input:
    def __init__(self):
        self.Buttons = np.zeros(Button_OnePastLast, dtype=np.int32);
        self.MouseX = 0.0;
        self.MouseY = 0.0;
        self.PrevButtons = np.zeros(Button_OnePastLast, dtype=np.int32);
        self.PrevMouseX = 0.0;
        self.PrevMouseY = 0.0;
    
    def EndFrame(self) -> None:
        self.PrevButtons = np.copy(self.Buttons);
        self.PrevMouseX = self.MouseX;
        self.PrevMouseY = self.MouseY;
    
    def IsDown(self, Button: int) -> int:
        Result = 0;
        if(0 <= Button and Button < Button_OnePastLast):
            Result = self.Buttons[Button];
        return Result;
    
    def WasDown(self, Button: int) -> int:
        Result = 0;
        if(0 <= Button and Button < Button_OnePastLast):
            Result = self.PrevButtons[Button];
        return Result;
    
    def IsPressed(self, Button: int) -> int:
        return self.IsDown(Button) and not self.WasDown(Button);
    
    def WasPressed(self, Button: int) -> int:
        return not self.IsDown(Button) and self.WasDown(Button);
    
    def InputDigit(self) -> str:
        if(self.IsPressed(Key_0)):  return '0';
        if(self.IsPressed(Key_1)):  return '1';
        if(self.IsPressed(Key_2)):  return '2';
        if(self.IsPressed(Key_3)):  return '3';
        if(self.IsPressed(Key_4)):  return '4';
        if(self.IsPressed(Key_5)):  return '5';
        if(self.IsPressed(Key_6)):  return '6';
        if(self.IsPressed(Key_7)):  return '7';
        if(self.IsPressed(Key_8)):  return '8';
        if(self.IsPressed(Key_9)):  return '9';
        return None;

Input = input();
Board = [];
first_start = False;
class loaded_glyph:
    def __init__(self, \
                 dX: float, dY: float, DimX: float, DimY: float, \
                 LeftSideBearing: float, Advance: float, \
                 TextureHandle: int):
        self.DimX = DimX;
        self.DimY = DimY;
        self.dX = dX;
        self.dY = dY;
        self.LeftSideBearing = LeftSideBearing;
        self.Advance = Advance;
        self.TextureHandle = TextureHandle;

class loaded_font:
    def __init__(self, Path: str):
        self.Handle = freetype.Face(Path);
        self.UnscaledHeight = 64;
        self.OnePastLastCodepoint = 256;
        self.Handle.set_char_size(0, self.UnscaledHeight*64);
        self.Ascent = self.Handle.size.ascender / 64;
        self.Descent = self.Handle.size.descender / 64;
        self.Glyphs = np.empty(self.OnePastLastCodepoint, dtype=object);
        for Index in range(self.OnePastLastCodepoint):
            self.Glyphs[Index] = None;

class assets:
    def __init__(self):
        self.Fonts = np.empty(Font_OnePastLast, dtype=object);
        for Index in range(Font_OnePastLast):
            self.Fonts[Index] = loaded_font("../font/Montserrat-Bold.ttf");

class render_group:
    def __init__(self, PixelPerMeter: int, DisplayWidth: int, DisplayHeight: int, CameraX: float, CameraY: float):
        self.DisplayWidth = DisplayWidth;
        self.DisplayHeight = DisplayHeight;
        self.PixelPerMeter = PixelPerMeter;
        self.CameraX = CameraX;
        self.CameraY = CameraY;

class ui_context:
    def __init__(self):
        self.HotID = UIID_Back;
        self.Input = None;
        self.Assets = None;
        self.RenderGroup = None;
        self.Exiting = 0;
        self.CreatingRoom = 0;
        self.JoinStep = 0;
        self.JoinRoomID = np.zeros(ROOM_ID_LENGTH, dtype=np.int32);
        
    def BeginFrame(self, Input: input, Assets: assets, RenderGroup: render_group) -> None:
        self.Input = Input;
        self.Assets = Assets;
        self.RenderGroup = RenderGroup;

class ui_layout:
    def __init__(self, Context: ui_context, X: float, Y: float):
        self.Context = Context;
        self.CursorX = X;
        self.CursorY = Y;
        self.LineHeight = 0.5;
        self.TooltipLineHeight = 0.2;
        self.Tooltip = "";
    
    def DoUIItem(self, ID: int, Label: str, Tooltip: str) -> int:
        Result = 0;
        Context = self.Context;
        MinX, MinY, MaxX, MaxY = GetStringRect(Context.RenderGroup, Context.Assets, self.LineHeight, Label);
        AtX = self.CursorX + MinX - (MaxX - MinX)/2;
        AtY = self.CursorY;
        
        Color = Color_MenuItem;
        if(Context.HotID == ID): 
            Color = Color_HotMenuItem;
        RenderString(Context.RenderGroup, Context.Assets, AtX+0.02, AtY-0.02, self.LineHeight, Label, v4(0, 0, 0, 1));
        RenderString(Context.RenderGroup, Context.Assets, AtX, AtY, self.LineHeight, Label, Color);
        if(Context.HotID == ID):
            self.Tooltip = Tooltip;
            if(Context.Input.IsPressed(Key_Space)):
                Result = 1;
        self.CursorY -= self.LineHeight*1.5;
        return Result;
    
    def DoTooltip(self) -> None:
        Context = self.Context;
        MinX, MinY, MaxX, MaxY = GetStringRect(Context.RenderGroup, Context.Assets, self.TooltipLineHeight, self.Tooltip);
        AtX = self.CursorX + MinX - (MaxX - MinX)/2;
        AtY = self.CursorY;
        RenderString(Context.RenderGroup, Context.Assets, AtX+0.01, AtY-0.01, self.TooltipLineHeight, self.Tooltip, v4(0, 0, 0, 1));
        RenderString(Context.RenderGroup, Context.Assets, AtX, AtY, self.TooltipLineHeight, self.Tooltip, Color_Tooltip);
        self.CursorY -= self.TooltipLineHeight*1.5;
        

class game_state:
    def __init__(self, BoardCountX: int, BoardCountY: int, BoardDim: int):
        self.Assets = assets();
        self.UIContext = ui_context();
        self.BoardCountX = BoardCountX;
        self.BoardCountY = BoardCountY;
        self.BoardDim = BoardDim;
        self.Mode = Mode_Game;
        self.SelectedMenuItem = 0;

Color_Background    = v4(0.976, 0.965, 0.914, 1.0);
Color_Board         = v4(0.733, 0.678, 0.627, 1.0);
Color_MenuItem      = v4(0.976, 0.965, 0.949, 1.0);
Color_HotMenuItem   = v4(0.965, 0.486, 0.376, 1.0);
Color_Tooltip       = v4(0.929, 0.878, 0.784, 1.0);

TextColors = np.empty(12, dtype=object);
TileColors = np.empty(12, dtype=object);
TextColors[ 0] = v4(0.000, 0.000, 0.000, 1.0);
TextColors[ 1] = v4(0.467, 0.431, 0.396, 1.0);
TextColors[ 2] = v4(0.467, 0.431, 0.396, 1.0);
TextColors[ 3] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[ 4] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[ 5] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[ 6] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[ 7] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[ 8] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[ 9] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[10] = v4(0.976, 0.965, 0.949, 1.0);
TextColors[11] = v4(0.976, 0.965, 0.949, 1.0);

TileColors[ 0] = v4(0.804, 0.753, 0.706, 1.0);
TileColors[ 1] = v4(0.933, 0.894, 0.855, 1.0);
TileColors[ 2] = v4(0.929, 0.878, 0.784, 1.0);
TileColors[ 3] = v4(0.949, 0.694, 0.475, 1.0);
TileColors[ 4] = v4(0.961, 0.584, 0.388, 1.0);
TileColors[ 5] = v4(0.965, 0.486, 0.376, 1.0);
TileColors[ 6] = v4(0.965, 0.369, 0.231, 1.0);
TileColors[ 7] = v4(0.929, 0.812, 0.451, 1.0);
TileColors[ 8] = v4(0.898, 0.773, 0.373, 1.0);
TileColors[ 9] = v4(0.882, 0.745, 0.298, 1.0);
TileColors[10] = v4(0.890, 0.737, 0.235, 1.0);
TileColors[11] = v4(0.890, 0.729, 0.169, 1.0);



def GetWallClock() -> int:
    ClockTime = time.perf_counter_ns();
    return ClockTime;

def LoadTexture(Width: int, Height: int, Buffer: np.array) -> int:
    TextureHandle = gl.glGenTextures(1);
    gl.glBindTexture(gl.GL_TEXTURE_2D, TextureHandle);
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_BORDER);
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_BORDER);
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR);
    gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR);
    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA8, \
                    Width, Height, \
                    0, gl.GL_BGRA, gl.GL_UNSIGNED_BYTE, \
                    Buffer);
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0);
    return TextureHandle;

def LoadGlyph(Font: loaded_font, Codepoint: int) -> (float, float, float, float, int, int, np.array):
    Font.Handle.load_char(Codepoint);
    Glyph = Font.Handle.glyph;
    
    LeftSideBearing = Glyph.metrics.horiBearingX / 64.0;
    Advance = Glyph.metrics.horiAdvance / 64.0;
    Source = Glyph.bitmap.buffer;
    Width = Glyph.bitmap.width;
    Height = Glyph.bitmap.rows;
    dX = Glyph.metrics.horiBearingX / 64.0;
    dY = Glyph.metrics.horiBearingY / 64.0 - Height;
    
    Data = np.empty((Height, Width, 4), dtype=np.uint8);
    for y in range(Height):
        for x in range(Width):
            Pixel = Source[Width*(Height-(y+1)) + x];
            Data[y, x, 0] = 255;
            Data[y, x, 1] = 255;
            Data[y, x, 2] = 255;
            Data[y, x, 3] = Pixel;
    return dX, dY, LeftSideBearing, Advance, Width, Height, Data;

def GetFont(Assets: assets, FontID: int) -> loaded_font:
    return Assets.Fonts[FontID];

def GetGlyph(Font: loaded_font, Codepoint: int) -> loaded_glyph:
    Result = None;
    assert(Font is not None);
    if((0 <= Codepoint) and (Codepoint < Font.OnePastLastCodepoint)):
        if(Font.Glyphs[Codepoint] is None):
            dX, dY, LeftSideBearing, Advance, Width, Height, Data = LoadGlyph(Font, Codepoint);
            TextureHandle = LoadTexture(Width, Height, Data);
            Font.Glyphs[Codepoint] = loaded_glyph(dX, dY, Width, Height, LeftSideBearing, Advance, TextureHandle);
        Result = Font.Glyphs[Codepoint];
    return Result;

def GetKerning(Font: loaded_font, A: float, B: float) -> (float, float):
    X = 0;
    Y = 0;
    if(Font.Handle.has_kerning):
        Kerning = Font.Handle.get_kerning(A, B, freetype.FT_KERNING_UNFITTED);
        X = Kerning.x / 64;
        Y = Kerning.y / 64;
    return X, Y;

def RenderBitmap(Group: render_group, X: float, Y: float, Width: float, Height: float, Color: v4, TextureHandle: int) -> None:
    HalfWidthPerMeter = 2.0*Group.PixelPerMeter / Group.DisplayWidth;
    HalfHeightPerMeter = 2.0*Group.PixelPerMeter / Group.DisplayHeight;
    dX = (Group.CameraX - 0.5)*2;
    dY = (Group.CameraY - 0.5)*2;
    MinX = X * HalfWidthPerMeter + dX;
    MinY = Y * HalfHeightPerMeter + dY;
    MaxX = (X + Width) * HalfWidthPerMeter + dX;
    MaxY = (Y + Height) * HalfHeightPerMeter + dY;
    
    gl.glBindTexture(gl.GL_TEXTURE_2D, TextureHandle);
    gl.glBegin(gl.GL_TRIANGLES);
    gl.glColor4f(Color.R, Color.G, Color.B, Color.A);
    gl.glTexCoord2f(0.0, 0.0);
    gl.glVertex3f(MinX, MinY, 0.0);
    gl.glTexCoord2f(1.0, 0.0);
    gl.glVertex3f(MaxX, MinY, 0.0);
    gl.glTexCoord2f(0.0, 1.0);
    gl.glVertex3f(MinX, MaxY, 0.0);
    
    gl.glTexCoord2f(1.0, 0.0);
    gl.glVertex3f(MaxX, MinY, 0.0);
    gl.glTexCoord2f(1.0, 1.0);
    gl.glVertex3f(MaxX, MaxY, 0.0);
    gl.glTexCoord2f(0.0, 1.0);
    gl.glVertex3f(MinX, MaxY, 0.0);
    gl.glEnd();
    gl.glBindTexture(gl.GL_TEXTURE_2D, 0);

def RenderQuad(Group: render_group, X: float, Y: float, Width: float, Height: float, Color: v4) -> None:
    RenderBitmap(Group, X, Y, Width, Height, Color, 0);

def RenderBorder(Group: render_group, X: float, Y: float, Width: float, Height: float, Color: v4) -> None:
    RenderQuad(Group, X, Y, Width, 0.02, Color);
    RenderQuad(Group, X, Y, 0.02, Height, Color);
    RenderQuad(Group, X+Width, Y, 0.02, Height, Color);
    RenderQuad(Group, X, Y+Height, Width, 0.02, Color);

def RenderString(Group: render_group, Assets: assets, \
                 X: float, Y: float, LineHeight: float, String: str, Color: v4, DimOnly: int = 0) -> (float, float, float, float):
    MinX = X;
    MinY = Y;
    MaxX = X;
    MaxY = Y;
    Font = GetFont(Assets, Font_Game);
    assert(Font is not None);
    Scale = LineHeight / Font.UnscaledHeight;
    PrevCodepoint = 0;
    for Codepoint in String:
        Glyph = GetGlyph(Font, ord(Codepoint));
        if(Glyph is not None):
            KerningX, KerningY = GetKerning(Font, PrevCodepoint, Codepoint);
            X += KerningX*Scale;
            AtX = X + (Glyph.dX + KerningX)*Scale;
            AtY = Y + (Glyph.dY + KerningY)*Scale;
            DimX = Glyph.DimX*Scale;
            DimY = Glyph.DimY*Scale;
            if(DimOnly == 0):
                #RenderBorder(Group, AtX, AtY, DimX, DimY, Color);
                RenderBitmap(Group, AtX, AtY, DimX, DimY, Color, Glyph.TextureHandle);
            if(AtX < MinX): MinX = AtX;
            if(AtY < MinY): MinY = AtY;
            if(AtX + DimX > MaxX): MaxX = AtX + DimX;
            if(AtY + DimY > MaxY): MaxY = AtY + DimY;
            X += Glyph.Advance*Scale;
            PrevCodepoint = Codepoint;
    return MinX, MinY, MaxX, MaxY;

def GetStringRect(Group: render_group, Assets: assets, LineHeight: float, String: str) -> (float, float, float, float):
    return RenderString(Group, Assets, 0, 0, LineHeight, String, v4(0, 0, 0, 0), 1);

def RenderBoard(Group: render_group, Assets: assets, AtX: float, AtY: float, BoardDim: float, Board: np.array):
    global TileColors;
    global TextColors;
    HalfDim = BoardDim * 0.5;
    BorderDim = BoardDim * 0.032;
    TileDim = (BoardDim - BorderDim*5) / 4;
    
    RenderQuad(Group, AtX - HalfDim, AtY - HalfDim, BoardDim, BoardDim, Color_Board);
    for TileY in range(4):
        for TileX in range(4):
            X = AtX - HalfDim + (TileDim*TileX) + (BorderDim*(TileX+1));
            Y = AtY - HalfDim + (TileDim*TileY) + (BorderDim*(TileY+1));
            
            Shift = int(Board[TileY*4 + TileX]);
            RenderQuad(Group, X, Y, TileDim, TileDim, TileColors[Shift % TileColors.size]);
            
            if(Shift > 0):
                Text = str(1 << Shift);
                LineHeight = BoardDim*0.1;
                MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, LineHeight, Text);
                MaxTextRatio = 0.8;
                if(MaxX-MinX > TileDim * MaxTextRatio): 
                    LineHeight *= TileDim * MaxTextRatio / (MaxX-MinX);
                    MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, LineHeight, Text);
                RenderString(Group, Assets, \
                             X+TileDim*0.5 - (MaxX-MinX)*0.5, \
                             Y+TileDim*0.5 - (MaxY*0.5), LineHeight, \
                             Text, TextColors[Shift % TextColors.size]);
    
    Score = 3465413;
    ScoreLineHeight = BoardDim * 0.075;
    ScoreText = "Score: " + str(Score);
    MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, ScoreLineHeight, ScoreText);
    ScoreWidth = MaxX - MinX;
    RenderString(Group, Assets, 
                 X + TileDim - ScoreWidth, Y+TileDim + ScoreLineHeight, \
                 ScoreLineHeight, \
                 ScoreText, v4(0, 0, 0, 1));
def add_two(mat):
    Board = mat
    column_produce = random.randint(0,3)
    row_produce = random.randint(0,3)
    while Board[row_produce*4+column_produce]!=0:
        column_produce = random.randint(0,3)
        row_produce = random.randint(0,3)
    Board[row_produce*4+column_produce] = 1
    return Board

def UpdateAndRenderGame(Game: game_state, DisplayWidth: int, DisplayHeight: int, BoardTemp) -> None:
    global Input;
    global first_start
    RenderGroup = render_group(125, DisplayWidth, DisplayHeight, 0.5, 0.5);
    Game.UIContext.BeginFrame(Input, Game.Assets, RenderGroup);
    
    if(Input.IsPressed(Key_Escape)):
        if(Game.Mode == Mode_Game):     Game.Mode = Mode_Menu;
        elif(Game.Mode == Mode_Menu):   Game.Mode = Mode_Game;
    
    if(Game.Mode == Mode_Game):
        if(Input.IsPressed(Key_DevPlus)):
            Game.BoardDim += 1;
        if(Input.IsPressed(Key_DevMinus) and Game.BoardDim > 1):
            Game.BoardDim -= 1;
        if(Input.IsPressed(Key_Dev6)):
            Game.BoardCountX += 1;
        if(Input.IsPressed(Key_Dev4) and Game.BoardCountX > 1):
            Game.BoardCountX -= 1;
        if(Input.IsPressed(Key_Dev8)):
            Game.BoardCountY += 1;
        if(Input.IsPressed(Key_Dev2) and Game.BoardCountY > 1):
            Game.BoardCountY -= 1;
    
    BorderWidth = Game.BoardDim * 0.25;
    Boards = np.empty(Game.BoardCountX*Game.BoardCountY, dtype=object);
    BoardXs = np.empty(Game.BoardCountX, dtype=object);
    BoardYs = np.empty(Game.BoardCountY, dtype=object);
    
    for Index in range(Game.BoardCountX*Game.BoardCountY):
        Boards[Index] = BoardTemp;
        Board = Boards[Index];

    if first_start == False:
        #for Index in range(Game.BoardCountX*Game.BoardCountY):
        Board = add_two(Board)
        Board = add_two(Board)
        for y in range(4):
            for x in range(4):
                Board[y*4+x] = 1;        
        first_start = True
        

    if(Game.Mode == Mode_Game):
        if(Input.IsPressed(Key_Left)):
            for k in range(3):
                for row in range(4):
                    for col in range(3):
                        if Board[row*4+col]==0 and Board[row*4+col+1]!=0:
                            Board[row*4+col],Board[row*4+col+1] = Board[row*4+col+1],Board[row*4+col]
            for row in range(4):
                for col in range(3):
                    if Board[row*4+col] == Board[row*4+col+1] and Board[row*4+col]!=0:
                        Board[row*4+col] = Board[row*4+col]+1
                        Board[row*4+col+1] = 0
            for k in range(3):
                for row in range(4):
                    for col in range(3):
                        if Board[row*4+col]==0 and Board[row*4+col+1]!=0:
                            Board[row*4+col],Board[row*4+col+1] = Board[row*4+col+1],Board[row*4+col]
            Board = add_two(Board)
        elif(Input.IsPressed(Key_Right)):
            for k in range(3):
                for row in range(4):
                    for col in range(3,0,-1):
                        if Board[row*4+col]==0 and Board[row*4+col-1]!=0:
                            Board[row*4+col],Board[row*4+col-1] = Board[row*4+col-1],Board[row*4+col]
            for row in range(4):
                for col in range(3,0,-1):
                    if Board[row*4+col] == Board[row*4+col-1] and Board[row*4+col]!=0:
                        Board[row*4+col] = Board[row*4+col]+1
                        Board[row*4+col-1] = 0
            for k in range(3):
                for row in range(4):
                    for col in range(3,0,-1):
                        if Board[row*4+col]==0 and Board[row*4+col-1]!=0:
                            Board[row*4+col],Board[row*4+col-1] = Board[row*4+col-1],Board[row*4+col]
            Board = add_two(Board)
        elif(Input.IsPressed(Key_Down)):
            for k in range(3):
                for col in range(4):
                    for row in range(3):
                        if Board[row*4+col]==0 and Board[(row+1)*4+col]!=0:
                            Board[row*4+col],Board[(row+1)*4+col] = Board[(row+1)*4+col],Board[row*4+col]
            for col in range(4):
                for row in range(3):
                    if Board[row*4+col] == Board[(row+1)*4+col] and Board[row*4+col]!=0:
                        Board[row*4+col] = Board[row*4+col]+1
                        Board[(row+1)*4+col] = 0
            for k in range(3):
                for col in range(4):
                    for row in range(3):
                        if Board[row*4+col]==0 and Board[(row+1)*4+col]!=0:
                            Board[row*4+col],Board[(row+1)*4+col] = Board[(row+1)*4+col],Board[row*4+col]
            
            Board = add_two(Board)
        elif(Input.IsPressed(Key_Up)):
            for k in range(3):
                for col in range(4):
                    for row in range(3,0,-1):
                        if Board[row*4+col]==0 and Board[(row-1)*4+col]!=0:
                            Board[row*4+col],Board[(row-1)*4+col] = Board[(row-1)*4+col],Board[row*4+col]
            for col in range(4):
                for row in range(3,0,-1):
                    if Board[row*4+col] == Board[(row-1)*4+col] and Board[row*4+col]!=0:
                        Board[row*4+col] = Board[row*4+col]+1
                        Board[(row-1)*4+col] = 0
            for k in range(3):
                for col in range(4):
                    for row in range(3,0,-1):
                        if Board[row*4+col]==0 and Board[(row-1)*4+col]!=0:
                            Board[row*4+col],Board[(row-1)*4+col] = Board[(row-1)*4+col],Board[row*4+col]
            Board = add_two(Board)
    for Index in range(Game.BoardCountX):
        BoardXs[Index] = (Index - (Game.BoardCountX-1)/2) * (Game.BoardDim + BorderWidth);
    for Index in range(Game.BoardCountY):
        BoardYs[Index] = (Index - (Game.BoardCountY-1)/2) * (Game.BoardDim + BorderWidth);
    
    for y in range(Game.BoardCountY):
        for x in range(Game.BoardCountX):
            RenderBoard(RenderGroup, Game.Assets, BoardXs[x], BoardYs[y], Game.BoardDim, Boards[y*Game.BoardCountX+x]);
    
    if(Game.Mode == Mode_Menu):
        Context = Game.UIContext;
        if(Context.Input.IsPressed(Key_Up) and (Context.HotID > UIID_Back)):
            Context.HotID -= 1;
        if(Context.Input.IsPressed(Key_Down) and (Context.HotID < UIID_Exit)):
            Context.HotID += 1;
        
        ScreenRenderGroup = render_group(1, DisplayWidth, DisplayHeight, 0, 0);
        RenderQuad(ScreenRenderGroup, 0, 0, DisplayWidth, DisplayHeight, v4(0.0, 0.0, 0.0, 0.5));
        Layout = ui_layout(Context, 0.0, 1.5);
        Layout.DoUIItem(UIID_None, "In Room: 16516514", "14714653");
        if(Layout.DoUIItem(UIID_Back, "Back", "back to game")):
            Game.Mode = Mode_Game;
        
        CreateLabel = "Create Room";
        if(Context.CreatingRoom):
            CreateLabel = "trying...";
        if(Layout.DoUIItem(UIID_CreateRoom, CreateLabel, "create a new room")):
            Context.CreatingRoom = 1;
        
        JoinLabel = "Join Room";
        if(Context.JoinStep == 1):
            JoinLabel = "";
            for i in range(ROOM_ID_LENGTH):
                JoinLabel += chr(Context.JoinRoomID[i]);
            Digit = Context.Input.InputDigit();
            if((Digit is not None) and Context.JoinRoomCaret < ROOM_ID_LENGTH):
                Context.JoinRoomID[Context.JoinRoomCaret] = ord(Digit);
                Context.JoinRoomCaret += 1;
            if(Context.Input.IsPressed(Key_Backspace) and Context.JoinRoomCaret > 0):
                Context.JoinRoomCaret -= 1;
                Context.JoinRoomID[Context.JoinRoomCaret] = ord('_');
        elif(Context.JoinStep == 2):
            JoinLabel = "joining...";
        
        if(Layout.DoUIItem(UIID_JoinRoom, JoinLabel, "enter ID to join a room")):
            if(Context.JoinStep == 0):
                Context.JoinStep = 1;
                Context.JoinRoomCaret = 0;
                for i in range(ROOM_ID_LENGTH):
                    Context.JoinRoomID[i] = ord('_');
            elif(Context.JoinStep == 1):
                if(Context.JoinRoomCaret == ROOM_ID_LENGTH):
                    Context.JoinStep = 2;
                
        
        ExitLabel = "Exit";
        if(Context.Exiting):
            ExitLabel = "sure to exit?";
        if(Layout.DoUIItem(UIID_Exit, ExitLabel, "exit game")):
            if(Context.Exiting):
                exit(0);
            else:
                Context.Exiting = 1;
        
        if(Context.HotID != UIID_CreateRoom):   Context.CreatingRoom = 0;
        if(Context.HotID != UIID_JoinRoom):     Context.JoinStep = 0;
        if(Context.HotID != UIID_Exit):         Context.Exiting = 0;
        Layout.DoTooltip();
        
    Input.EndFrame();
    return Boards[0]

def KeyHandler(Window, Key: int, ScanCode: int, Action: int, Mods: int):
    IsDown = (Action == glfw.PRESS) or (Action == glfw.REPEAT);
    if(Key == glfw.KEY_RIGHT):          Input.Buttons[Key_Right     ] = IsDown;
    elif(Key == glfw.KEY_LEFT):         Input.Buttons[Key_Left      ] = IsDown;
    elif(Key == glfw.KEY_DOWN):         Input.Buttons[Key_Down      ] = IsDown;
    elif(Key == glfw.KEY_UP):           Input.Buttons[Key_Up        ] = IsDown;
    elif(Key == glfw.KEY_ENTER):        Input.Buttons[Key_Enter     ] = IsDown;
    elif(Key == glfw.KEY_ESCAPE):       Input.Buttons[Key_Escape    ] = IsDown;
    elif(Key == glfw.KEY_BACKSPACE):    Input.Buttons[Key_Backspace ] = IsDown;
    elif(Key == glfw.KEY_SPACE):        Input.Buttons[Key_Space     ] = IsDown;
    elif(Key == glfw.KEY_KP_0):         Input.Buttons[Key_0         ] = IsDown;
    elif(Key == glfw.KEY_KP_1):         Input.Buttons[Key_1         ] = IsDown;
    elif(Key == glfw.KEY_KP_2):         Input.Buttons[Key_2         ] = IsDown;
    elif(Key == glfw.KEY_KP_3):         Input.Buttons[Key_3         ] = IsDown;
    elif(Key == glfw.KEY_KP_4):         Input.Buttons[Key_4         ] = IsDown;
    elif(Key == glfw.KEY_KP_5):         Input.Buttons[Key_5         ] = IsDown;
    elif(Key == glfw.KEY_KP_6):         Input.Buttons[Key_6         ] = IsDown;
    elif(Key == glfw.KEY_KP_7):         Input.Buttons[Key_7         ] = IsDown;
    elif(Key == glfw.KEY_KP_8):         Input.Buttons[Key_8         ] = IsDown;
    elif(Key == glfw.KEY_KP_9):         Input.Buttons[Key_9         ] = IsDown;
    
    if(Key == glfw.KEY_KP_2):           Input.Buttons[Key_Dev2      ] = IsDown;
    elif(Key == glfw.KEY_KP_4):         Input.Buttons[Key_Dev4      ] = IsDown;
    elif(Key == glfw.KEY_KP_6):         Input.Buttons[Key_Dev6      ] = IsDown;
    elif(Key == glfw.KEY_KP_8):         Input.Buttons[Key_Dev8      ] = IsDown;
    elif(Key == glfw.KEY_KP_ADD):       Input.Buttons[Key_DevPlus   ] = IsDown;
    elif(Key == glfw.KEY_KP_SUBTRACT):  Input.Buttons[Key_DevMinus  ] = IsDown;

def MouseButtonHandler(Window, Button: int, Action: int, Mods: int):
    global Input;
    IsDown = (Action == glfw.PRESS);
    if(Button == glfw.MOUSE_BUTTON_LEFT):
        Input.Buttons[Mouse_Left] = IsDown;
    elif(Button == glfw.MOUSE_BUTTON_RIGHT):
        Input.Buttons[Mouse_Right] = IsDown;
    elif(Button == glfw.MOUSE_BUTTON_MIDDLE):
        Input.Buttons[Mouse_Middle] = IsDown;

def CursorMoveHandler(Window, X: float, Y: float):
    global Input;
    Input.MouseX = X;
    Input.MouseY = Y;

def main():
    global touch_once
    glfw.init();
    Window = glfw.create_window(1280, 720, "2048 battle", None, None);
    glfw.make_context_current(Window);
    
    gl.glEnable(gl.GL_BLEND);
    gl.glEnable(gl.GL_TEXTURE_2D);
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA);
    gl.glClearColor(Color_Background.R, Color_Background.G, Color_Background.B, Color_Background.A);
    
    glfw.set_key_callback(Window, KeyHandler);
    glfw.set_mouse_button_callback(Window, MouseButtonHandler);
    glfw.set_cursor_pos_callback(Window, CursorMoveHandler);
    GameState = game_state(2, 1, 4);
    
    GlobalRunning = True;
    FrameStart = GetWallClock();
    FrameEnd = FrameStart;
    BoardTemp = np.zeros(4*4, dtype=int)
    while GlobalRunning:
        WindowWidth, WindowHeight = glfw.get_framebuffer_size(Window);
        gl.glViewport(0, 0, WindowWidth, WindowHeight);
        gl.glClear(gl.GL_COLOR_BUFFER_BIT);
        Temp = UpdateAndRenderGame(GameState, WindowWidth, WindowHeight,BoardTemp);
        BoardTemp = Temp
        glfw.swap_buffers(Window);
        if(glfw.window_should_close(Window)):
            GlobalRunning = False;
        FrameEnd = GetWallClock();
        TimeElapsed = (FrameEnd - FrameStart) / 1000000000;
        TargetSecondPerFrame = 1.0 / 30.0;
        RemainTime = TargetSecondPerFrame - TimeElapsed;
        if(RemainTime < 0.0):
            RemainTime = 0.0;
        glfw.wait_events_timeout(RemainTime);
        FrameStart = FrameEnd;

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)

async def handle_ws1(ws: WebSocketClientProtocol):
    type, data = await next_event(ws)
    logging.info(("ws1", type, data))
    assert type == "connected"
    await asyncio.sleep(1)
    await send_event(ws, ClientUpdateMessage(123, 64))
    await asyncio.sleep(1)
    await send_event(ws, ClientUpdateMessage(8763, 512))
    await asyncio.sleep(2)
    await send_event(ws, ClientWinMessage(8763))
    async for type, data in receive_events(ws):
        logging.info(("ws1", type, data))
        if type == "disconnected":
            await ws.close()
            break


async def handle_ws2(ws: WebSocketClientProtocol):
    type, data = await next_event(ws)
    logging.info(("ws2", type, data))
    assert type == "connected"
    await asyncio.sleep(3)
    await send_event(ws, ClientUpdateMessage(3535, 256))
    async for type, data in receive_events(ws):
        logging.info(("ws2", type, data))
        if type == "opponent_win":
            await ws.close()
            break

async def test_message():
    async with connect("ws://localhost:1357") as ws1, connect(
        "ws://localhost:1357"
    ) as ws2:
        await send_event(ws1, NewRoomRequest())
        type, data = await anext(receive_events(ws1))
        logging.info((type, data))
        assert type == "new_room_id"
        await send_event(ws2, ConnectRequest(data.room_id))
        await asyncio.gather(handle_ws1(ws1), handle_ws2(ws2))

if __name__ == "__main__":
    main();
    #asyncio.run(test_message())
