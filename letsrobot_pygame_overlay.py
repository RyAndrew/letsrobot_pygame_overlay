import os
import pygame
import pygame.freetype
import pygame.display
import time
import random
from time import sleep
import sys
import datetime


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
        drivers = ['directfb','fbcon', 'directfb', 'svgalib']
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
            print "using driver ",driver
            break


        if not found:
            raise Exception('No suitable video driver found!')
        
        size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        print "Fullscreen Framebuffer size: %d x %d" % (size[0], size[1])
        self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)

        print "display init complete"

        pygame.freetype.init()

        pygame.mouse.set_visible(False)
        
        # Clear the screen with black
        self.screen.fill((0, 0, 0))        

        pygame.display.update()

        self.percentage = True
        self.cpustat = '/proc/stat'
        self.sep = ' ' 
        self.sleeptime = .5

        self.font = pygame.freetype.SysFont('Verdana', 24, bold=True)

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
        cpu_infos = {} #collect here the information
        with open(self.cpustat,'r') as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line.startswith('cpu')]

            #compute for every cpu
            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('')#remove empty elements
                cpu_line = [cpu_line[0]]+[float(i) for i in cpu_line[1:]]#type casting
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest,guest_nice = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal

                Total=Idle+NonIdle
                #update dictionionary
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle}})
            return cpu_infos

    def getcpuload(self):
        '''
        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        '''
        start = self.getcputime()
        #wait a second
        sleep(self.sleeptime)
        stop = self.getcputime()

        cpu_load = {}

        for cpu in start:
            Total = stop[cpu]['total']
            PrevTotal = start[cpu]['total']

            Idle = stop[cpu]['idle']
            PrevIdle = start[cpu]['idle']

            TotalDelta = Total-PrevTotal

            if TotalDelta == 0:
                CPU_Percentage=0
            else:
                CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/TotalDelta*100

            cpu_load.update({cpu: CPU_Percentage})

        cpu_all_cores_avg = (cpu_load["cpu0"]+cpu_load["cpu1"]+cpu_load["cpu2"]+cpu_load["cpu3"])/4
        return str(round(cpu_all_cores_avg,1))
    
    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    def measure_temp(self):
        temp = os.popen("vcgencmd measure_temp").readline()
        return (temp.replace("temp=",""))

    def sec2time(self, sec, n_msec=0):
        ''' Convert seconds to 'D days, HH:MM:SS.FFF' '''
        if hasattr(sec,'__len__'):
            return [sec2time(s) for s in sec]
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if n_msec > 0:
            pattern = '%%02d:%%02d:%%0%d.%df' % (n_msec+3, n_msec)
        else:
            pattern = r'%02d:%02d:%02d'
        if d == 0:
            return pattern % (h, m, s)
        return ('%d days, ' + pattern) % (d, h, m, s)
    
    def getWifiStats(self):
        os.popen("cat /proc/net/wireless >> python_overlay_wifi.tmp")
        qualityCmd = "awk 'NR==3 {print $3}' python_overlay_wifi.tmp"
        strQuality = os.popen(qualityCmd).read()

        dbmCmd = "awk 'NR==3 {print $4}' python_overlay_wifi.tmp"
        strDbm = os.popen(dbmCmd).read()

        if strDbm:
            qualityInt = int(float(strQuality.strip()))
            qualityPercent = qualityInt * 10/7

            dbmInt = int(float(strDbm.strip()))
            return "{0}% {1}dBm".format(qualityPercent, dbmInt)
        else:
            return "Not Found"
        
    def drawText(self, text, x=0,y=0,clearScreen=True):
        
        textsurface,rect = self.font.render(text, (255, 0, 0))
        self.screen.blit(textsurface,(x,y))

    def checkTimeDelta(self, last, interval):
        now = datetime.datetime.now()
        delta = now - last
        secondsElapsed = delta.total_seconds()

        #print "headlights delta ",headlightSecondsElapsed
        if secondsElapsed > interval:
            return True
        else:
            return False

    def printDateTimeOutput(self, text):
        print str(datetime.datetime.now()) , text

overlay = pythonvideooverlay()

#first time for uptime calculation
now = datetime.datetime.now()
startTime = now

StatsWifi = overlay.getWifiStats()
StatsWifiLastReading = now
StatsWifiInterval = 3

StatsTemp = overlay.measure_temp().strip()
StatsTempLastReading = now
StatsTempInterval = 4

StatsCpu = overlay.getcpuload()
StatsCpuLastReading = now
StatsCpuInterval = 2

overlay.printDateTimeOutput("starting video loop!")

while True:
    try:

        #clear the screen
        overlay.screen.fill((0, 0, 0))   

        nowTime = datetime.datetime.now()
        delta = nowTime - startTime
        overlay.drawText("Uptime: "+overlay.sec2time(delta.total_seconds()), 10, 10, True)

        if overlay.checkTimeDelta(StatsTempLastReading, StatsTempInterval):
            StatsTemp = overlay.measure_temp().strip()
            StatsTempLastReading = datetime.datetime.now()
            overlay.printDateTimeOutput("read temp!")

        overlay.drawText("Temp: "+StatsTemp, 10, 40, False)

        if overlay.checkTimeDelta(StatsWifiLastReading, StatsWifiInterval):
            StatsWifi = overlay.getWifiStats()
            StatsWifiLastReading = datetime.datetime.now()
            overlay.printDateTimeOutput("read wifi!")

        overlay.drawText("Wifi: "+StatsWifi, 10, 68, False)

        if overlay.checkTimeDelta(StatsCpuLastReading, StatsCpuInterval):
            StatsCpu = overlay.getcpuload()
            StatsCpuLastReading = datetime.datetime.now()
            overlay.printDateTimeOutput("read cpu!")

        #this call waits 1 second to capture avg cpu usage
        overlay.drawText("CPU: "+StatsCpu+"%", 10, 96, False)

        #update the screen
        pygame.display.update()
        overlay.printDateTimeOutput("update screen!")

        sleep(.5)

    except KeyboardInterrupt:
        sys.exit("KeyboardInterrupt")   
