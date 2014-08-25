'''
Created on Aug 22, 2014

@author: zwicker
'''


import multiprocessing
import time

from .simple import scan_video
from video.io.base import VideoFork
from video.io.pipe import VideoPipe
from video.filters import FilterCrop


QUADRANTS = {'UL': 'upper left',
             'DL': 'lower left',
             'UR': 'upper right',
             'DR': 'lower right'}
  


def scan_video_quadrants(video, **kwargs):
    """ Takes a video and scans all four quadrants in parallel.
    Here, the video is read in one process, split into four video streams
    and analyzed in four separate processes
    Additional parameters include a dictionary 'parameters'
    """
    
    # create a fork, such that the data can be analyzed by multiple consumers
    video_fork = VideoFork(video, synchronized=True, client_count=len(QUADRANTS))
    
    pipes = []
    for name, crop in QUADRANTS.iteritems():
        # crop the video to the right region
        video_crop = FilterCrop(video_fork, region=crop, color_channel=1)
        # construct the video sender 
        video_pipe = VideoPipe(video_crop, name=name)
        # launch a new process, where the receiver is going to live 
        proc = multiprocessing.Process(target=scan_video,
                                       args=(video_pipe.receiver, video_pipe.name),
                                       kwargs=kwargs)

        proc.start()
        pipes.append(video_pipe)
    
    try:
        # start the main loop where we check all senders periodically
        while any(video_pipe.running for video_pipe in pipes):
            # check if any senders are running
            for video_pipe in pipes:
                video_pipe.check()
    
            # let the CPU rest a little
            time.sleep(0.001)
        
    except (KeyboardInterrupt, SystemExit):
        # try to interrupt the system cleanly
        for video_pipe in pipes:
            video_pipe.abort_iteration()
        
    