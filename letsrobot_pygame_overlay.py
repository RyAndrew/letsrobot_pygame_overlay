import os
import pygame
import pygame.freetype
import pygame.display
import pygame.camera
import time
import random
from time import sleep
import sys
import datetime
import serial

DEVICE = '/dev/video0'
SIZE = (800,448)
FILENAME = 'capture.png'


# credit first goes to adafruit!
# https://learn.adafruit.com/pi-video-output-using-pygame/pointing-pygame-to-the-framebuffer

class pythonvideooverlay:
    screen = None;

    def __init__(self):
        "Ininitializes a new pygame screen using the framebuffer"
        # Based on "Python GUI in Linux frame buffer"
        # http://www.karoltomala.com/blog/?p=679
        os.environ["SDL_FBDEV"] = "/dev/fb0"

        disp_no = os.getenv("DISPLAY")
        if disp_no:
            print "I'm running under X display = {0}".format(disp_no)
    
        # Check which frame buffer drivers are available
        # Start with fbcon since directfb hangs with composite output
        drivers = ['directfb', 'fbcon', 'directfb', 'svgalib']
        found = False

        for driver in drivers:
            # Make sure that SDL_VIDEODRIVER is set
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)
            try:
                pygame.display.init()
            except pygame.error:
                print 'Driver: {0} failed.'.format(driver)
                continue
            found = True
            print "using driver ", driver
            break

        if not found:
            raise Exception('No suitable video driver found!')

#         Fullscreen Framebuffer
#         size: 640x480
#         [(1600, 1200), (1280, 1024), (1024, 1024), (1280, 960), (1152, 864), (1024, 768), (800, 600), (768, 576),
#          (640, 480)]
# < VideoInfo(hw=1, wm=0, video_mem=1200
# blit_hw = 0, blit_hw_CC = 0, blit_hw_A = 0,
# blit_sw = 0, blit_sw_CC = 0, blit_sw_A = 0,
# bitsize = 16, bytesize = 2,
# masks = (
# 63488,
# 2016,
# 31,
# 0),
# shifts = (
# 11,
# 5,
# 0,
# 0),
# losses = (
# 3,
# 2,
# 3,
# 8),
# current_w = 640, current_h = 480>

        size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        print "Fullscreen Framebuffer size: %d x %d" % (size[0], size[1])
        # print pygame.display.mode_ok()
        print pygame.display.list_modes()
        print pygame.display.Info()

        self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
        # self.screen = pygame.display.set_mode(size, pygame.DOUBLEBUF, 16)
        # pygame.display.set_mode((600, 400), 0, 32)

        print "display init complete"

        pygame.mouse.set_visible(False)

        pygame.freetype.init()

        # Clear the screen with black
        # self.screen.fill((0, 0, 0))
        self.screen.fill(0)

        pygame.display.update()

        self.percentage = True
        self.cpustat = '/proc/stat'
        self.sep = ' '
        self.sleeptime = .5

        self.font = pygame.freetype.SysFont('Verdana', 18, bold=True)

    def getcputime(self):
        '''
        http://stackoverflow.com/questions/23367857/accurate-calculation-of-cpu-usage-given-in-percentage-in-linux
        read in cpu information from file
        The meanings of the columns are as follows, from left to right:
            0cpuid: number of cpu
            1user: normal processes executing in user mode
            2nice: niced processes executing in user mode
            3system: processes executing in kernel mode
            4idle: twiddling thumbs
            5iowait: waiting for I/O to complete
            6irq: servicing interrupts
            7softirq: servicing softirqs

        #the formulas from htop
             user    nice   system  idle      iowait irq   softirq  steal  guest  guest_nice
        cpu  74608   2520   24433   1117073   6176   4054  0        0      0      0


        Idle=idle+iowait
        NonIdle=user+nice+system+irq+softirq+steal
        Total=Idle+NonIdle # first line of file for all cpus

        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        '''
        cpu_infos = {}  # collect here the information
        with open(self.cpustat, 'r') as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if
                     line.startswith('cpu')]

            # compute for every cpu
            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('')  # remove empty elements
                cpu_line = [cpu_line[0]] + [float(i) for i in cpu_line[1:]]  # type casting
                cpu_id, user, nice, system, idle, iowait, irq, softrig, steal, guest, guest_nice = cpu_line

                Idle = idle + iowait
                NonIdle = user + nice + system + irq + softrig + steal

                Total = Idle + NonIdle
                # update dictionionary
                cpu_infos.update({cpu_id: {'total': Total, 'idle': Idle}})
            return cpu_infos

    def getcpuload(self, start, stop):
        '''
        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        '''

        cpu_load = {}

        for cpu in start:
            Total = stop[cpu]['total']
            PrevTotal = start[cpu]['total']

            Idle = stop[cpu]['idle']
            PrevIdle = start[cpu]['idle']

            TotalDelta = Total - PrevTotal

            if TotalDelta == 0:
                CPU_Percentage = 0
            else:
                CPU_Percentage = ((Total - PrevTotal) - (Idle - PrevIdle)) / TotalDelta * 100

            cpu_load.update({cpu: CPU_Percentage})

        cpu_all_cores_avg = (cpu_load["cpu0"] + cpu_load["cpu1"] + cpu_load["cpu2"] + cpu_load["cpu3"]) / 4
        return str(round(cpu_all_cores_avg, 1))

    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    def measure_temp(self):
        temp = os.popen("vcgencmd measure_temp").readline()
        return (temp.replace("temp=", ""))

    def sec2time(self, sec, n_msec=0):
        ''' Convert seconds to 'D days, HH:MM:SS.FFF' '''
        if hasattr(sec, '__len__'):
            return [sec2time(s) for s in sec]
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if n_msec > 0:
            pattern = '%%02d:%%02d:%%0%d.%df' % (n_msec + 3, n_msec)
        else:
            pattern = r'%02d:%02d:%02d'
        if d == 0:
            return pattern % (h, m, s)
        return ('%d days, ' + pattern) % (d, h, m, s)

    def getWifiStats(self):
        cmd = "awk 'NR==3 {print $3,\"|\",$4}' /proc/net/wireless"
        strQualityDbm = os.popen(cmd).read()

        if strQualityDbm:
            strQualityDbmSplit = strQualityDbm.split('|')
            strQuality = strQualityDbmSplit[0].strip()
            strDbm = strQualityDbmSplit[1].strip()

            qualityInt = int(float(strQuality))
            qualityPercent = qualityInt * 10 / 7

            dbmInt = int(float(strDbm))
            return "{0}% {1}dBm".format(qualityPercent, dbmInt)
        else:
            return "Not Found"

    def drawText(self, text, x=0, y=0, previousRect=None):

        # if previousRect != None:

        textsurface, rect = self.font.render(text, (255, 0, 0), None)
        return self.screen.blit(textsurface, (x, y))

    def checkTimeDelta(self, last, interval):
        now = datetime.datetime.now()
        delta = now - last
        secondsElapsed = delta.total_seconds()

        # print "headlights delta ",headlightSecondsElapsed
        if secondsElapsed > interval:
            return True
        else:
            return False

    def printDateTimeOutput(self, text):
        dateNow = datetime.datetime.now()
        print dateNow.strftime("%Y-%m-%d %H:%M:%S"), text


motorRpms = {
    'A': 0,
    'B': 0
}

battery = {
    'voltage': 0,
    'power': 0
}

def tryToGetAFloat(str):
    try:
        returnVal = float(str)
    except ValueError:
        returnVal = 0
    return returnVal


def readSerial():
    serialStr = arduinoSerial.readline(10)
    if serialStr and len(serialStr) > 1:
        rawSerial = repr(serialStr)
        # overlay.printDateTimeOutput("raw: " + repr(serialStr))
        if len(serialStr) > 10:
            overlay.printDateTimeOutput("Serial Junk > 8")
            overlay.printDateTimeOutput("raw: " + rawSerial)
            arduinoSerial.flushInput()
            motorRpms['A'] = 0
            motorRpms['B'] = 0
        else:
            # overlay.printDateTimeOutput("raw: " + repr(serialStr))
            # serialStr = serialStr.strip()
            serialStr = serialStr.replace("\x00", "")
            serialStr = serialStr.replace("\r", "")
            serialStr = serialStr.replace("\n", "")
            # overlay.printDateTimeOutput("raw: " + repr(serialStr))
            # overlay.printDateTimeOutput("Serial Recvd: " + serialStr)
            serialCommand = serialStr.split("=")
            if len(serialCommand) < 2:
                overlay.printDateTimeOutput("Invalid serial command!")
                overlay.printDateTimeOutput("raw: " + rawSerial)
                arduinoSerial.flushInput()
                motorRpms['A'] = 0
                motorRpms['B'] = 0
            else:
                if len(serialCommand[1]) < 1:
                    overlay.printDateTimeOutput("Invalid serial value!")
                    overlay.printDateTimeOutput("raw: " + rawSerial)
                    motorRpms['A'] = 0
                    motorRpms['B'] = 0
                else:
                    # overlay.printDateTimeOutput("raw val: " + repr(serialCommand[1]))
                    if serialCommand[0] == 'MA': #Motor A
                        motorRpms['A'] = tryToGetAFloat(serialCommand[1])
                    elif serialCommand[0] == 'MB': #Motor B
                        motorRpms['B'] = tryToGetAFloat(serialCommand[1])
                    elif serialCommand[0] == 'BP': #battery power
                        battery['power'] = tryToGetAFloat(serialCommand[1])
                        overlay.printDateTimeOutput("batteryPower: " + serialCommand[1])
                    elif serialCommand[0] == 'BV': #battery voltage
                        battery['voltage'] = tryToGetAFloat(serialCommand[1])
                        overlay.printDateTimeOutput("batteryVoltage: " + serialCommand[1])
                    else:
                        overlay.printDateTimeOutput("Unknown serial command!")
                        overlay.printDateTimeOutput("raw: " + rawSerial)


overlay = pythonvideooverlay()

# first time for uptime calculation
now = datetime.datetime.now()
startTime = now

StatsWifi = overlay.getWifiStats()
StatsWifiLastReading = now
StatsWifiInterval = 3

StatsTemp = overlay.measure_temp().strip()
StatsTempLastReading = now
StatsTempInterval = 4

StatsCpuLastReading = now
StatsCpuInterval = 2
StatsCpuStartLoad = overlay.getcputime()
sleep(1)
StatsCpuEndLoad = overlay.getcputime()
StatsCpu = overlay.getcpuload(StatsCpuStartLoad, StatsCpuEndLoad)

fpsAvg30Sec = "{:.1f}".format(0)

arduinoSerial = serial.Serial(
    port='/dev/ttyS0', \
    baudrate=115200, \
    parity=serial.PARITY_NONE, \
    stopbits=serial.STOPBITS_ONE, \
    bytesize=serial.EIGHTBITS, \
    timeout=.01)
arduinoSerial.flushInput()


rectTime = None
rectTemp = None
rectWifi = None
rectCpu = None
rectMotorA = None
rectMotorB = None

print("connected to arduino on serial port " + arduinoSerial.portstr)

overlay.printDateTimeOutput("starting webcam")
pygame.camera.init()
camera = pygame.camera.Camera(DEVICE, SIZE)
camera.start()
cameraSurface = pygame.surface.Surface(SIZE, 0, overlay.screen)

overlay.printDateTimeOutput("starting video update loop!")

fpsCalcTimeLastOutput = datetime.datetime.now()
cameraCaptureTimeLastOutput = datetime.datetime.now()
cameraCaptureTimeTicks = 0
cameraCaptureTimeSum = 0
loopIterations = 0
while True:
    try:
        loopIterations += 1
        fpsCalcTimeDelta = datetime.datetime.now() - fpsCalcTimeLastOutput
        fpsCalcTimeDeltaElapsed = fpsCalcTimeDelta.total_seconds()
        if fpsCalcTimeDeltaElapsed > 30:
            fpsCalcTimeLastOutput = datetime.datetime.now()
            fpsAvg30Sec = "{:.1f}".format(loopIterations/fpsCalcTimeDeltaElapsed)
            overlay.printDateTimeOutput("last 30s avg fps="+fpsAvg30Sec)
            loopIterations = 0

        # cameraCaptureTime = datetime.datetime.now()

        cameraImage = camera.get_image(cameraSurface)

        # cameraCaptureTimeDelta = datetime.datetime.now() - cameraCaptureTime
        # cameraCaptureTimeDeltaSeconds = cameraCaptureTimeDelta.total_seconds()
        # cameraCaptureTimeSum += cameraCaptureTimeDeltaSeconds
        # cameraCaptureTimeTicks += 1
        #
        # if cameraCaptureTimeTicks > 10:
        #     avgCamLatency = cameraCaptureTimeSum / cameraCaptureTimeTicks
        #     overlay.printDateTimeOutput("last 10 fames capture time avg="+str(avgCamLatency))
        #     cameraCaptureTimeTicks = 0
        #     cameraCaptureTimeSum = 0

        overlay.screen.blit(cameraImage, (0, 0))
        # pygame.display.flip()

        # clear the screen
        # overlay.screen.fill((0, 0, 0))
        # overlay.screen.fill(0)

        nowTime = datetime.datetime.now()
        delta = nowTime - startTime
        rectTime = overlay.drawText("Uptime " + overlay.sec2time(delta.total_seconds()), 10, 5, rectTime)

        if overlay.checkTimeDelta(StatsTempLastReading, StatsTempInterval):
            StatsTemp = overlay.measure_temp().strip()
            StatsTempLastReading = datetime.datetime.now()
            # overlay.printDateTimeOutput("read temp!")

        rectTemp = overlay.drawText("Temp " + StatsTemp, 10, 25, rectTemp)

        if overlay.checkTimeDelta(StatsWifiLastReading, StatsWifiInterval):
            StatsWifi = overlay.getWifiStats()
            StatsWifiLastReading = datetime.datetime.now()
            # overlay.printDateTimeOutput("read wifi!")

        rectWifi = overlay.drawText("Wifi " + StatsWifi, 10, 45, rectWifi)

        if overlay.checkTimeDelta(StatsCpuLastReading, StatsCpuInterval):
            StatsCpuEndLoad = overlay.getcputime()
            StatsCpu = overlay.getcpuload(StatsCpuStartLoad, StatsCpuEndLoad)
            StatsCpuStartLoad = overlay.getcputime()
            StatsCpuLastReading = datetime.datetime.now()
            # overlay.printDateTimeOutput("read cpu!")

        # this call waits 1 second to capture avg cpu usage
        rectCpu = overlay.drawText("CPU " + StatsCpu + "%", 10, 65, rectCpu)

        overlay.drawText("30s avg fps " + fpsAvg30Sec , 10, 85 )

        readSerial()
        readSerial()
        readSerial()
        readSerial()
        # arduinoSerial.flushInput()
        #8.4 is full, 6.24 is dead
        # 8.4 - 6.24 = 2.19
        # 8.4 - 2.19 = 6.24
        batteryPercent = ((battery['voltage'] - 2.19) / 6.24)*100
        overlay.drawText("Battery " + format(batteryPercent, '.0f') + "% " + format(battery['voltage'], '.2f') + "V " + format(battery['power'],'.0f') + "mW", 440, 5, rectMotorB)

        if motorRpms['A'] > 0:
            # overlay.printDateTimeOutput("Motor A: " + str(motorRpms['A']) + " rpm")
            rectMotorA = overlay.drawText("Motor A: " + str(motorRpms['A']) + " rpm", 440, 25, rectMotorA)
        else:
            rectMotorA = None
        if motorRpms['B'] > 0:
            # overlay.printDateTimeOutput("Motor B: " + str(motorRpms['B']) + " rpm")
            rectMotorB = overlay.drawText("Motor B: " + str(motorRpms['B']) + " rpm", 440, 45, rectMotorB)
        else:
            rectMotorB = None


        # pygame.display.flip()

        # update the screen
        # overlay.printDateTimeOutput("update screen!")
        #pygame.display.flip()
        pygame.display.update()
        #pygame.display.update((rectTime, rectTemp, rectWifi, rectCpu, rectMotorA,rectMotorB))

#        if cameraCaptureTimeDeltaSeconds < .01:
#            sleep(.001)

    except KeyboardInterrupt:
        overlay.printDateTimeOutput("quitting!")
        camera.stop()
        pygame.quit()
        sys.exit("KeyboardInterrupt")
