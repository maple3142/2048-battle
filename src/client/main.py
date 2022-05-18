import asyncio
from websockets.client import connect, WebSocketClientProtocol
from messages import *
from shared_utils import receive_events, next_event, send_event
import logging
import os
from typing import Tuple

import numpy as np
import glfw
import time
import OpenGL.GL as gl
import freetype
import threading
import queue
import random

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

TargetFPS = 60.0;
TargetSecondPerFrame = 1.0 / TargetFPS;

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

class key_frame:
    def __init__(self, X0: float, Y0: float, R0: float, X1: float, Y1: float, R1: float, t1: float, Value: int, LoopCount: int):
        self.X0 = X0;
        self.Y0 = Y0;
        self.R0 = R0;
        self.X1 = X1;
        self.Y1 = Y1;
        self.R1 = R1;
        self.t1 = t1;
        self.Value = Value;
        self.LoopCount = LoopCount;

class animation:
    def __init__(self):
        self.Frames = np.empty(0, dtype=object);
        self.t = 0.0;
    
    def AddFrame(self, X0: float, Y0: float, R0: float, X1: float, Y1: float, R1: float, t1: float, Value: int, LoopCount: int = 1):
        Frame = key_frame(X0, Y0, R0, X1, Y1, R1, t1, Value, LoopCount);
        self.Frames = np.append(self.Frames, Frame);
    
    def Lerp(self, dt: float) -> Tuple[float, float, float, int]:
        X = 0; Y = 0; R = 0; Value = 0;
        self.t += dt;
        
        if(self.Frames.size > 0):
            Frame = self.Frames[0];
            Value = Frame.Value;
            delta = self.t / Frame.t1;
            if(delta < 0.0):    delta = 0.0;
            elif(delta > 1.0):  delta = 1.0;
            a = np.sin(delta*np.pi/2);
            X = (1.0-a)*Frame.X0 + a*Frame.X1;
            Y = (1.0-a)*Frame.Y0 + a*Frame.Y1;
            R = (1.0-a)*Frame.R0 + a*Frame.R1;
            if(self.t > Frame.t1):
                self.t -= Frame.t1;
                if(Frame.LoopCount > 0):
                    Frame.LoopCount -= 1;
                    if(Frame.LoopCount == 0):
                        self.Frames = np.delete(self.Frames, 0);
        return X, Y, R, Value;

class ui_context:
    def __init__(self):
        self.HotID = UIID_Back;
        self.Input = None;
        self.Assets = None;
        self.RenderGroup = None;
        self.Exiting = 0;
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
    def __init__(self, BoardCountX: int, BoardCountY: int, BoardDim: int, \
                 EventLoop: asyncio.AbstractEventLoop, \
                 ToServerQueue: asyncio.Queue, ToClientQueue: queue):
        self.Assets = assets();
        self.UIContext = ui_context();
        self.BoardCountX = BoardCountX;
        self.BoardCountY = BoardCountY;
        self.BoardDim = BoardDim;
        self.Mode = Mode_Game;
        self.SelectedMenuItem = 0;
        self.Boards = np.empty(0, dtype=object);
        self.EventLoop = EventLoop;
        self.ToServerQueue = ToServerQueue;
        self.ToClientQueue = ToClientQueue;
        self.RoomID = "no";
        self.WaitingInRoom = 0;
        self.Connected = 0;
        self.CreatingRoomCount = 0;
        self.ConnectingRoomID = [];

class board:
    def __init__(self):
        self.VX = 1;
        self.VY = 1;
        self.Pack = np.empty(4*4, dtype=object);
        self.Mat0 = np.zeros(4*4, dtype=np.int32);
        self.Mat = np.zeros(4*4, dtype=np.int32);
        self.Xs = None;
        self.Ys = None;
        self.Rs = None;
        self.Ss = None;
        self.Score = 0;
        self.ScoreAnimation = animation();
        self.WinAnimation = animation();
        self.ScoreAnimation.AddFrame(0, 0, 1, 0, 0, 1, 1, self.Score, 0);
        self.WinAnimation.AddFrame(0, 0, 1, 0, 0, 1, 1, 0, 0);
        for i in range(4*4):
                self.Pack[i] = animation();
        for y in range(4):
            for x in range(4):
                self.Mat0[y*4+x] = 0;
                self.Pack[y*4+x].AddFrame(x, y, 1, x, y, 1, 1, self.Mat0[y*4+x], 0);
    
    def BeginMoveBoard(self, VX: int, VY: int):
        self.VX = VX;
        self.VY = VY;
        self.Mat = np.copy(self.Mat0);
        self.Xs = np.empty(4*4, dtype=np.int32);
        self.Ys = np.empty(4*4, dtype=np.int32);
        self.Rs = np.zeros(4*4, dtype=np.int32);
        self.Ss = np.zeros(4*4, dtype=np.int32);
        for y in range(4):
            for x in range(4):
                self.Xs[y*4+x] = x;
                self.Ys[y*4+x] = y;
    
    def Move(self, X0: float, Y0: float, X1: float, Y1: float) -> None:
        self.Mat[Y1*4+X1] = self.Mat[Y0*4+X0];
        self.Mat[Y0*4+X0] = 0;
        self.Rs[Y1*4+X1] = self.Rs[Y0*4+X0];
        self.Rs[Y0*4+X0] = 0;
        for i in range(4*4):
            if(self.Xs[i] == X0 and self.Ys[i] == Y0):
                self.Xs[i] = X1;
                self.Ys[i] = Y1;
        #print("MOV: (%d,%d)->(%d,%d)" % (X0, Y0, X1, Y1));
    
    def Scoring(self, Value: int):
        self.Score = Value;
        self.ScoreAnimation = animation();
        self.ScoreAnimation.AddFrame(0, 0, 0.8, 0, 0, 1.2, 0.1, self.Score);
        self.ScoreAnimation.AddFrame(0, 0, 1.2, 0, 0, 1.0, 0.2, self.Score);
        self.ScoreAnimation.AddFrame(0, 0, 1, 0, 0, 1, 1, self.Score, 0);
    
    def Raise(self, X: float, Y: float, Value: int) -> None:
        self.Mat[Y*4+X] = Value;
        self.Rs[Y*4+X] = 1;
        self.Scoring(self.Score + (1 << Value));
        #print("MERGE: (%d,%d) -> %d" % (X, Y, Value));
    
    def Delete(self, X: float, Y: float) -> None:
        self.Mat[Y*4+X] = 0;
        #print("DEL: (%d,%d)" % (X, Y));
    
    def Spawn(self, Value: int) -> None:
        Location = [];
        for i in range(4*4):
            if(self.Mat[i] == 0):
                Location.append(i);
        if(len(Location) > 0):
            Index = random.randint(0, len(Location)-1);
            X = Location[Index] & 3;
            Y = Location[Index] >> 2;
            self.Mat[Y*4+X] = Value;
            self.Ss[Y*4+X] = 1;
    
    def HasChanged(self) -> int:
        for y in range(4):
            for x in range(4):
                if(self.Mat0[y*4+x] != self.Mat[y*4+x]):
                    return 1;
        return 0;
    
    def EndMoveBoard(self):
        DoneFirstRaise = np.zeros(4*4, dtype=np.int32);
        Xs = [3, 2, 1, 0]; Ys = [3, 2, 1, 0];
        if(self.VX < 0): Xs = range(4);
        if(self.VY < 0): Ys = range(4);
        for Y0 in Ys:
            for X0 in Xs:
                Index = Y0*4+X0;
                X1 = self.Xs[Index];
                Y1 = self.Ys[Index];
                self.Pack[Index] = animation();
                Animation = self.Pack[Index];
                Animation.AddFrame(X0, Y0, 1, X1, Y1, 1, 0.133, self.Mat0[Y0*4+X0]);
                if(self.Rs[Y1*4+X1] and not DoneFirstRaise[Y1*4+X1]):
                    Animation.AddFrame(X1, Y1, 0.2, X1, Y1, 1.1, 0.067, self.Mat[Y1*4+X1]);
                    Animation.AddFrame(X1, Y1, 1.1, X1, Y1, 1.0, 0.100, self.Mat[Y1*4+X1]);
                    DoneFirstRaise[Y1*4+X1] = 1;
                else:
                    Animation.AddFrame(X1, Y1, 1, X1, Y1, 1, 0.067, self.Mat0[Y0*4+X0]);
                #print("(%f,%f) -> (%f,%f) [Raise=%d/%d]" % (X0, Y0, X1, Y1, self.Rs[Index], (Y1*4+X1 != Index)));
        for Y in Ys:
            for X in Xs:
                Index = Y*4+X;
                Animation = self.Pack[Index];
                if(self.Ss[Y*4+X]):
                    Animation.AddFrame(X, Y, 0.2, X, Y, 1.1, 0.067, self.Mat[Y*4+X]);
                    Animation.AddFrame(X, Y, 1.1, X, Y, 1.0, 0.100, self.Mat[Y*4+X]);
                Animation.AddFrame(X, Y, 1, X, Y, 1, 1, self.Mat[Y*4+X], 0);
        self.Mat0 = np.copy(self.Mat);

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

Input = input();

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

def LoadGlyph(Font: loaded_font, Codepoint: int) -> Tuple[float, float, float, float, int, int, np.array]:
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

def GetKerning(Font: loaded_font, A: float, B: float) -> Tuple[float, float]:
    X = 0;
    Y = 0;
    if(Font.Handle.has_kerning):
        Kerning = Font.Handle.get_kerning(A, B, freetype.FT_KERNING_UNFITTED);
        X = Kerning.x / 64;
        Y = Kerning.y / 64;
    return X, Y;

def RenderBitmap(Group: render_group, X: float, Y: float, Width: float, Height: float, Color: v4, TextureHandle: int) -> None:
    HalfWidthPerMeter = 0;
    HalfHeightPerMeter = 0;
    if(Group.DisplayWidth > 0):
        HalfWidthPerMeter = 2.0*Group.PixelPerMeter / Group.DisplayWidth;
    if(Group.DisplayHeight > 0):
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
                 X: float, Y: float, LineHeight: float, String: str, Color: v4, DimOnly: int = 0) -> Tuple[float, float, float, float]:
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

def GetStringRect(Group: render_group, Assets: assets, LineHeight: float, String: str) -> Tuple[float, float, float, float]:
    return RenderString(Group, Assets, 0, 0, LineHeight, String, v4(0, 0, 0, 0), 1);

def RenderBoard(Group: render_group, Assets: assets, \
                BoardX: float, BoardY: float, BoardDim: float, \
                Board: board, dt: float):
    global TileColors;
    global TextColors;
    HalfDim = BoardDim * 0.5;
    BorderDim = BoardDim * 0.032;
    TileDim = (BoardDim - BorderDim*5) / 4;
    
    RenderQuad(Group, BoardX - HalfDim, BoardY - HalfDim, BoardDim, BoardDim, Color_Board);
    Frame = Board.Pack[0].Frames[0];
    for TileY in range(4):
        for TileX in range(4):
            RenderQuad(Group, (BoardX-HalfDim) + BorderDim + (TileDim+BorderDim)*TileX, (BoardY-HalfDim) + BorderDim + (TileDim+BorderDim)*TileY, TileDim, TileDim, TileColors[0]);
    
    Xs = range(4);
    Ys = range(4);
    if(Board.VX < 0): Xs = [3, 2, 1, 0];
    if(Board.VY < 0): Ys = [3, 2, 1, 0];
    for TileY in Ys:
        for TileX in Xs:
            Animation = Board.Pack[TileY*4 + TileX];
            AtX, AtY, AtR, Value = Animation.Lerp(dt);
            
            X = (BoardX-HalfDim) + BorderDim + (TileDim+BorderDim)*AtX + (1-AtR)/2*TileDim;
            Y = (BoardY-HalfDim) + BorderDim + (TileDim+BorderDim)*AtY + (1-AtR)/2*TileDim;
            R = AtR*TileDim;
    
            Shift = int(Value);
            if(Shift > 0):
                RenderQuad(Group, X, Y, R, R, TileColors[Shift % TileColors.size]);
                Text = str(1 << Shift);
                LineHeight = R*0.5;
                MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, LineHeight, Text);
                MaxTextRatio = 0.8;
                if(MaxX-MinX > R * MaxTextRatio): 
                    LineHeight *= R * MaxTextRatio / (MaxX-MinX);
                    MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, LineHeight, Text);
                RenderString(Group, Assets, \
                             X+R*0.5 - (MaxX-MinX)*0.5, Y+R*0.5 - (MaxY*0.5), \
                             LineHeight, \
                             Text, TextColors[Shift % TextColors.size]);
    
    Animation = Board.ScoreAnimation;
    AtX, AtY, AtR, Score = Animation.Lerp(dt);
    ScoreLineHeight = BoardDim * 0.075 * AtR;
    ScoreText = "Score: " + str(Score);
    MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, ScoreLineHeight, ScoreText);
    ScoreWidth = MaxX - MinX;
    RenderString(Group, Assets, 
                 BoardX+HalfDim - ScoreWidth, BoardY+HalfDim + ScoreLineHeight*0.4, \
                 ScoreLineHeight, \
                 ScoreText, v4(0, 0, 0, 1));
    
    Animation = Board.WinAnimation;
    AtX, AtY, AtR, WinLose = Animation.Lerp(dt);
    if(WinLose != 0):
        Banner = "Lose";
        BannerColor = v4(1.000, 0.000, 0.212, 1);
        ShadowColor = v4(0.500, 0.000, 0.106, 1);
        if(WinLose > 0):
            Banner = "Win!";
            BannerColor = v4(0.937, 0.855, 0.298, 1);
            ShadowColor = v4(0.300, 0.250, 0.100, 1);
        BannerLineHeight = BoardDim * 0.25 * AtR;
        MinX, MinY, MaxX, MaxY = GetStringRect(Group, Assets, BannerLineHeight, Banner);
        RenderString(Group, Assets, 
                     BoardX - (MaxX-MinX)*0.5+BannerLineHeight*0.02, BoardY - (MaxY*0.5)-BannerLineHeight*0.02, \
                     BannerLineHeight, \
                     Banner, ShadowColor);
        RenderString(Group, Assets, 
                     BoardX - (MaxX-MinX)*0.5, BoardY - (MaxY*0.5), \
                     BannerLineHeight, \
                     Banner, BannerColor);
        

def PrintAnimation(Animation: animation):
    for i in range(Animation.Frames.size):
        print("[%d]: (%f, %f) -> (%f, %f) in %fs (%f) [Value:%d]" % (i, Animation.Frames[i].X0, Animation.Frames[i].Y0, Animation.Frames[i].X1, Animation.Frames[i].Y1, Animation.Frames[i].t1, Animation.t, Animation.Frames[i].Value));

def UpdateAndRenderGame(Game: game_state, DisplayWidth: int, DisplayHeight: int) -> None:
    dt = TargetSecondPerFrame;
    if(Game.Boards.size > 0):
        if(Game.Boards[0].WinAnimation.Frames.size > 1): dt *= 0.05;
    while True:
        try:
            Message = Game.ToClientQueue.get_nowait();
            Board = Game.Boards[Message.PlayerID];
            if(Message.Type == "new_room_id"):
                if(Game.CreatingRoomCount > 0):
                    Game.WaitingInRoom = 1;
                    Game.Connected = 0;
                    Game.CreatingRoomCount -= 1;
                    Game.RoomID = Message.Data.room_id;
                    Game.ConnectingRoomID.append(Game.RoomID);
            elif(Message.Type == "connected"):
                if(len(Game.ConnectingRoomID) > 0):
                    Game.RoomID = Game.ConnectingRoomID.pop();
                    Game.WaitingInRoom = 0;
                    Game.Connected = 1;
                    for PlayerIndex in range(Game.BoardCountX*Game.BoardCountY):
                        Game.Boards[PlayerIndex] = board();
                    Game.Boards[0].BeginMoveBoard(1, 1);
                    Game.Boards[0].Spawn(1);
                    Game.Boards[0].EndMoveBoard();
            elif(Message.Type == "disconnected"):
                Game.WaitingInRoom = 0;
                Game.Connected = 0;
                Game.RoomID = "no";
                QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, None, 1);
            elif(Message.Type == "opponent_update"):
                Game.Boards[1].Scoring(Message.Data.score);
                if(Message.Data.penalty_block is not None):
                    Value = Message.Data.penalty_block;
                    Shift = 0;
                    while True: 
                        if(Value <= 1):
                            Game.Boards[0].BeginMoveBoard(1, 1);
                            Game.Boards[0].Spawn(Shift);
                            Game.Boards[0].EndMoveBoard();
                            break;
                        else:
                            Value = Value >> 1;
                            Shift += 1;
            elif(Message.Type == "opponent_win"):
                Game.WaitingInRoom = 0;
                Game.Connected = 0;
                Game.RoomID = "no";
                QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, None, 1);
                Game.Boards[0].WinAnimation = animation();
                Game.Boards[0].WinAnimation.AddFrame(0, 0, 0.6, 0, 0, 1.1, 0.075, -1);
                Game.Boards[0].WinAnimation.AddFrame(0, 0, 1.1, 0, 0, 1.0, 0.075, -1);
                Game.Boards[0].WinAnimation.AddFrame(0, 0, 1.0, 0, 0, 1.0, 0.250, -1);
                Game.Boards[0].WinAnimation.AddFrame(0, 0, 1.0, 0, 0, 1.0, 1, 0, 0);
        except queue.Empty:
            break;
    
    global Input;
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
    
    PlayerCount = Game.BoardCountX*Game.BoardCountY;
    BoardXs = np.empty(PlayerCount, dtype=object);
    BoardYs = np.empty(PlayerCount, dtype=object);
    BorderWidth = Game.BoardDim * 0.25;
    for BoardY in range(Game.BoardCountY):
        for BoardX in range(Game.BoardCountX):
            Index = BoardY*Game.BoardCountX + BoardX;
            BoardXs[Index] = (BoardX - (Game.BoardCountX-1)/2) * (Game.BoardDim + BorderWidth);
            BoardYs[Index] = (BoardY - (Game.BoardCountY-1)/2) * (Game.BoardDim + BorderWidth);
    
    if(PlayerCount != Game.Boards.size):
        Boards = np.empty(PlayerCount, dtype=object);
        for Index in range(PlayerCount):
            if(Index < Game.Boards.size):
                Boards[Index] = Game.Boards[Index];
            else:
                Boards[Index] = board();
                Boards[Index].BeginMoveBoard(1, 1);
                Boards[Index].Spawn(1);
                Boards[Index].EndMoveBoard();
        Game.Boards = Boards;
    
    Board = Game.Boards[0];
    for i in range(4*4):
        if(Board.Mat[i] == 5 and Game.Connected):
            Game.Connected = 0;
            QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, ClientWinMessage(int(Board.Score)));
            Game.Boards[0].WinAnimation = animation();
            Game.Boards[0].WinAnimation.AddFrame(0, 0, 0.6, 0, 0, 1.1, 0.075, 1);
            Game.Boards[0].WinAnimation.AddFrame(0, 0, 1.1, 0, 0, 1.0, 0.075, 1);
            Game.Boards[0].WinAnimation.AddFrame(0, 0, 1.0, 0, 0, 1.0, 0.250, 1);
            Game.Boards[0].WinAnimation.AddFrame(0, 0, 1.0, 0, 0, 1.0, 1, 0, 0);
    
    if(Game.Mode == Mode_Game):
        for PlayerIndex in range(1):
            Board = Game.Boards[PlayerIndex];
            if(Board.WinAnimation.Frames.size <= 1):
                if(Input.IsPressed(Key_Up)):
                    Board.BeginMoveBoard(1, 1);
                    for k in range(3):
                        for x in range(4):
                            for y in [2,1,0]:
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[(y+1)*4+x] == 0):
                                    Board.Move(x, y, x, y+1);
                    for x in range(4):
                        for y in [2,1,0]:
                            if(Board.Mat[y*4+x] == Board.Mat[(y+1)*4+x] and Board.Mat[y*4+x] != 0):
                                Value = Board.Mat[y*4+x] + 1;
                                Board.Delete(x, y+1);
                                Board.Move(x, y, x, y+1);
                                Board.Raise(x, y+1, Value);
                                if(Game.Connected):
                                    QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, \
                                                         ClientUpdateMessage(int(Board.Score), int(1 << Value)));
                    for k in range(3):
                        for x in range(4):
                            for y in [2,1,0]:
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[(y+1)*4+x] == 0):
                                    Board.Move(x, y, x, y+1);
                    if(Board.HasChanged()):
                        Board.Spawn(1);
                    Board.EndMoveBoard();
                if(Input.IsPressed(Key_Down)):
                    Board.BeginMoveBoard(1, -1);
                    for k in range(3):
                        for x in range(4):
                            for y in range(1, 4):
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[(y-1)*4+x] == 0):
                                    Board.Move(x, y, x, y-1);
                    for x in range(4):
                        for y in range(1, 4):
                            if(Board.Mat[y*4+x] == Board.Mat[(y-1)*4+x] and Board.Mat[y*4+x] != 0):
                                Value = Board.Mat[y*4+x] + 1;
                                Board.Delete(x, y-1);
                                Board.Move(x, y, x, y-1);
                                Board.Raise(x, y-1, Value);
                                if(Game.Connected):
                                    QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, \
                                                         ClientUpdateMessage(int(Board.Score), int(1 << Value)));
                    for k in range(3):
                        for x in range(4):
                            for y in range(1, 4):
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[(y-1)*4+x] == 0):
                                    Board.Move(x, y, x, y-1);
                    if(Board.HasChanged()):
                        Board.Spawn(1);
                    Board.EndMoveBoard();
                if(Input.IsPressed(Key_Left)):
                    Board.BeginMoveBoard(-1, 1);
                    for k in range(3):
                        for y in range(4):
                            for x in range(1, 4):
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[y*4+x-1] == 0):
                                    Board.Move(x, y, x-1, y);
                    for y in range(4):
                        for x in range(1, 4):
                            if(Board.Mat[y*4+x] == Board.Mat[y*4+x-1] and Board.Mat[y*4+x] != 0):
                                Value = Board.Mat[y*4+x] + 1;
                                Board.Delete(x-1, y);
                                Board.Move(x, y, x-1, y);
                                Board.Raise(x-1, y, Value);
                                if(Game.Connected):
                                    QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, \
                                                         ClientUpdateMessage(int(Board.Score), int(1 << Value)));
                    for k in range(3):
                        for y in range(4):
                            for x in range(1, 4):
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[y*4+x-1] == 0):
                                    Board.Move(x, y, x-1, y);
                    if(Board.HasChanged()):
                        Board.Spawn(1);
                    Board.EndMoveBoard();
                if(Input.IsPressed(Key_Right)):
                    Board.BeginMoveBoard(1, 1);
                    for k in range(3):
                        for y in range(4):
                            for x in [2,1,0]:
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[y*4+x+1] == 0):
                                    Board.Move(x, y, x+1, y);
                    for y in range(4):
                        for x in [2,1,0]:
                            if(Board.Mat[y*4+x] == Board.Mat[y*4+x+1] and Board.Mat[y*4+x] != 0):
                                Value = Board.Mat[y*4+x] + 1;
                                Board.Delete(x+1, y);
                                Board.Move(x, y, x+1, y);
                                Board.Raise(x+1, y, Value);
                                if(Game.Connected):
                                    QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, \
                                                         ClientUpdateMessage(int(Board.Score), int(1 << Value)));
                    for k in range(3):
                        for y in range(4):
                            for x in [2,1,0]:
                                if(Board.Mat[y*4+x] != 0 and Board.Mat[y*4+x+1] == 0):
                                    Board.Move(x, y, x+1, y);
                    if(Board.HasChanged()):
                        Board.Spawn(1);
                    Board.EndMoveBoard();
    
    for Index in range(PlayerCount):
        RenderBoard(RenderGroup, Game.Assets, \
                    BoardXs[Index], BoardYs[Index], Game.BoardDim, \
                    Game.Boards[Index], dt);
    
    if(Game.Mode == Mode_Menu):
        Context = Game.UIContext;
        if(Context.Input.IsPressed(Key_Up) and (Context.HotID > UIID_Back)):
            Context.HotID -= 1;
        if(Context.Input.IsPressed(Key_Down) and (Context.HotID < UIID_Exit)):
            Context.HotID += 1;
        
        if(Context.HotID != UIID_JoinRoom):     Context.JoinStep = 0;
        if(Context.HotID != UIID_Exit):         Context.Exiting = 0;
        
        ScreenRenderGroup = render_group(1, DisplayWidth, DisplayHeight, 0, 0);
        RenderQuad(ScreenRenderGroup, 0, 0, DisplayWidth, DisplayHeight, v4(0.0, 0.0, 0.0, 0.5));
        Layout = ui_layout(Context, 0.0, 1.5);
        Hint = "waiting";
        if(Game.Connected): Hint = "connected";
        Layout.DoUIItem(UIID_None, "In Room: %s (%s)" % (Game.RoomID, Hint), "");
        if(Layout.DoUIItem(UIID_Back, "Back", "back to game")):
            Game.Mode = Mode_Game;
        
        CreateLabel = "Create Room";
        if(Game.CreatingRoomCount > 0):
            CreateLabel = "trying...";
        if(Layout.DoUIItem(UIID_CreateRoom, CreateLabel, "create a new room")):
            Game.CreatingRoomCount += 1;
            QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, None, 1);
            QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, NewRoomRequest());
        
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
            if(len(Game.ConnectingRoomID) == 0):
                Context.JoinStep = 0;
            else:
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
                    RoomID = "";
                    for i in range(ROOM_ID_LENGTH):
                        RoomID = RoomID + chr(Context.JoinRoomID[i]);
                    Game.ConnectingRoomID.append(RoomID);
                    QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, None, 1);
                    QueueToServerMessage(Game.EventLoop, Game.ToServerQueue, 0, ConnectRequest(RoomID));
                
        
        ExitLabel = "Exit";
        if(Context.Exiting):
            ExitLabel = "sure to exit?";
        if(Layout.DoUIItem(UIID_Exit, ExitLabel, "exit game")):
            if(Context.Exiting):
                exit(0);
            else:
                Context.Exiting = 1;
        
        Layout.DoTooltip();
            
    Input.EndFrame();

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

class to_client_message:
    def __init__(self, PlayerID: int, Type: int, Data):
        self.PlayerID = PlayerID;
        self.Type = Type;
        self.Data = Data;

class to_server_message:
    def __init__(self, PlayerID: int, Data, GonnaByeBye: int):
        self.PlayerID = PlayerID;
        self.Data = Data;
        self.GonnaByeBye = GonnaByeBye;

async def OneClientListenEvent(Queue: queue, ID: int, Client: WebSocketClientProtocol):
    async for Type, Data in receive_events(Client):
        Message = to_client_message(ID, Type, Data);
        Queue.put(Message);

async def WorkerSendToServerMessage(EventLoop: asyncio.AbstractEventLoop, \
                                    ToServerQueue: asyncio.Queue, ToClientQueue: queue, \
                                    Clients: list[WebSocketClientProtocol]):
    while True:
        Message = await ToServerQueue.get();
        if(Clients[Message.PlayerID] is None):
            Clients[Message.PlayerID] = await connect("ws://localhost:1357");
            EventLoop.create_task(OneClientListenEvent(ToClientQueue, Message.PlayerID, Clients[Message.PlayerID]));
        if(Message.GonnaByeBye):
            if(Clients[Message.PlayerID] is not None):
                await Clients[Message.PlayerID].close();
                Clients[Message.PlayerID] = None;
        else:
            await send_event(Clients[Message.PlayerID], Message.Data);
        ToServerQueue.task_done();

async def MessageLoop(EventLoop: asyncio.AbstractEventLoop, \
                      ToServerQueue: asyncio.Queue, ToClientQueue: queue, \
                      Clients: list[WebSocketClientProtocol]):
    #async with connect("ws://localhost:1357") as ws1, \
    #           connect("ws://localhost:1357") as ws2:
    EventLoop.create_task(WorkerSendToServerMessage(EventLoop, ToServerQueue, ToClientQueue, Clients));
    Tasks = asyncio.all_tasks(EventLoop);
    await asyncio.gather(*Tasks);

def MessageThread(EventLoop: asyncio.AbstractEventLoop, \
                  ToServerQueue: asyncio.Queue, ToClientQueue: queue, \
                  Clients: list[WebSocketClientProtocol]):
    asyncio.set_event_loop(EventLoop);
    Task = EventLoop.create_task(MessageLoop(EventLoop, ToServerQueue, ToClientQueue, Clients));
    EventLoop.run_until_complete(Task);

async def PutToServerMessage(ToServerQueue: asyncio.Queue, ID: int, Data, GonnaByeBye:int):
    await ToServerQueue.put(to_server_message(ID, Data, GonnaByeBye));

def QueueToServerMessage(EventLoop: asyncio.AbstractEventLoop, \
                         ToServerQueue: asyncio.Queue, ID: int, Data, GonnaByeBye: int = 0):
    asyncio.run_coroutine_threadsafe(PutToServerMessage(ToServerQueue, ID, Data, GonnaByeBye), EventLoop);

def main():
    EventLoop = asyncio.new_event_loop();
    ToServerQueue = asyncio.Queue();
    ToClientQueue = queue.Queue();
    Clients = [None, None];
    ThreadHandle = threading.Thread(target=MessageThread, args=(EventLoop, ToServerQueue, ToClientQueue, Clients), daemon=True);
    ThreadHandle.start();
    
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
    GameState = game_state(2, 1, 4, EventLoop, ToServerQueue, ToClientQueue);
    
    GlobalRunning = True;
    FrameTime = 0.0;
    FrameStart = GetWallClock();
    FrameEnd = FrameStart;
    while GlobalRunning:
        WindowWidth, WindowHeight = glfw.get_framebuffer_size(Window);
        gl.glViewport(0, 0, WindowWidth, WindowHeight);
        gl.glClear(gl.GL_COLOR_BUFFER_BIT);
        global TargetSecondPerFrame;
        UpdateAndRenderGame(GameState, WindowWidth, WindowHeight);
        ScreenRenderGroup = render_group(1, WindowWidth, WindowHeight, 0, 0);
        FPS = 0.0;
        if(FrameTime != 0.0):
            FPS = 1000000000 / FrameTime;
        RenderString(ScreenRenderGroup, GameState.Assets, 0, 0, 18, "FPS: %f" % FPS, v4(1, 1, 1, 1));
        
        glfw.swap_buffers(Window);
        if(glfw.window_should_close(Window)):
            GlobalRunning = False;
        
        glfw.poll_events();
        FrameEnd = GetWallClock();
        TimeElapsed = (FrameEnd - FrameStart) / 1000000000;
        RemainTime = TargetSecondPerFrame - TimeElapsed;
        #wait_events_timeout precision makes people sad.
        while(RemainTime > 0.01):
            glfw.wait_events_timeout(RemainTime-0.01);
            FrameEnd = GetWallClock();
            TimeElapsed = (FrameEnd - FrameStart) / 1000000000;
            RemainTime = TargetSecondPerFrame - TimeElapsed
        while(RemainTime > 0.0):
            FrameEnd = GetWallClock();
            TimeElapsed = (FrameEnd - FrameStart) / 1000000000;
            RemainTime = TargetSecondPerFrame - TimeElapsed
        FrameTime = (FrameEnd - FrameStart);
        FrameStart = FrameEnd;

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)

async def handle_ws1(ws: WebSocketClientProtocol):
    type, data = await next_event(ws)
    logging.info(("ws1", type, data))
    assert type == "connected"
    await asyncio.sleep(1)
    board = [[0,2,0,2],[4,2,8,4],[2,8,16,0],[0,0,4,2]]
    await send_event(ws, ClientUpdateMessage(score=123, new_blocks=[64, 128], board=board, move_direction=Direction.UP))
    await asyncio.sleep(1)
    await send_event(ws, ClientUpdateMessage(score=8763, new_blocks=[512], board=board, move_direction=Direction.UP))
    await asyncio.sleep(1)
    await send_event(ws, ClientWinMessage(score=8763))
    await ws.close();
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
    board = [[0,2,0,2],[4,2,8,4],[2,8,16,0],[0,0,4,2]]
    await send_event(ws, ClientUpdateMessage(score=3535, new_blocks=[256], board=board,move_direction=Direction.LEFT))
    await ws.close();
    async for type, data in receive_events(ws):
        logging.info(("ws2", type, data))
        if type == "opponent_win":
            await ws.close()
            break

async def test_message():
    async with connect("ws://localhost:1357") as ws1, \
               connect("ws://localhost:1357") as ws2:
        await send_event(ws1, NewRoomRequest())
        type, data = await anext(receive_events(ws1))
        logging.info((type, data))
        assert type == "new_room_id"
        await send_event(ws2, ConnectRequest(data.room_id))
        await asyncio.gather(handle_ws1(ws1), handle_ws2(ws2))

if __name__ == "__main__":
    # main();
    asyncio.run(test_message())
