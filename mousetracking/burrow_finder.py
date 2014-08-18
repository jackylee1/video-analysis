'''
Created on Aug 16, 2014

@author: zwicker
'''

import itertools

import numpy as np
import cv2

from video.analysis.curves import make_curve_equidistant, simplify_curve
from video.analysis.regions import expand_rectangle, rect_to_slices

import debug


class BurrowFinder(object):
    """ class devoted to finding burrows in a image.
    This is a separate class because it might run in a separate process and
    the logic should separated from the main run
    """
    
    def __init__(self, tracking_parameters):
        self.params = tracking_parameters
        
                    
    #===========================================================================
    # FIND BURROWS 
    #===========================================================================

    def refine_burrow_outline(self, burrow, free_points):
        #burrow.show_image(free_points)
        
        # remove the fixed points from the final burrow object
        points = [p
                  for k, p in enumerate(burrow.outline)
                  if free_points[k]]
        
        return points


    def find_burrows(self, frame, frame_id, explored_area, ground_profile):
        """ locates burrows by combining the information of the ground profile
        and the explored area """
        
        # build a mask with potential burrows
        height, width = frame.shape
        ground_mask = np.zeros_like(frame, np.uint8)
        
        # create a mask for the region below the current ground profile
        ground_points = np.empty((len(ground_profile) + 4, 2), np.int)
        ground_points[:-4, :] = ground_profile
        ground_points[-4, :] = (width, ground_points[-5, 1])
        ground_points[-3, :] = (width, height)
        ground_points[-2, :] = (0, height)
        ground_points[-1, :] = (0, ground_points[0, 1])
        #ground_contour = np.array([ground_points], np.int)
        cv2.fillPoly(ground_mask, np.array([ground_points], np.int), color=128)

        # erode the mask slightly, since the ground profile is not perfect        
        w = self.params['ground/width'] + self.params['mouse/model_radius']
        # TODO: cache this kernel
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (w, w)) 
        cv2.erode(ground_mask, kernel, dst=ground_mask)
        
        w = self.params['burrows/radius']
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (w, w)) 
        cv2.morphologyEx(explored_area, cv2.MORPH_CLOSE, kernel, dst=explored_area)

        # combine with the information of what areas have been explored
        burrows_mask = cv2.bitwise_and(ground_mask, explored_area)
        
        # find the contours of the features
        contours, hierarchy = cv2.findContours(burrows_mask.copy(), # we want to use the mask later again
                                               cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
        
        burrows = []
        for contour in np.array(contours, np.int):
            # get enclosing rectangle 
            rect = cv2.boundingRect(contour)
            rect = expand_rectangle(rect, 30)
            
            # focus on this part of the problem
            slices = rect_to_slices(rect)
#             ground_mask_roi = ground_mask[slices]
#             burrow_mask = burrows_mask[slices]
            frame_roi = frame[slices]
            contour = np.squeeze(contour) - np.array([[rect[0], rect[1]]], np.int)

            # find the combined contour of burrow and ground profile
#             combined_mask = cv2.bitwise_xor(burrow_mask, ground_mask_roi)
            _, mask = cv2.threshold(frame_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            points, hierarchy = cv2.findContours(mask,
                                                 cv2.RETR_EXTERNAL,
                                                 cv2.CHAIN_APPROX_SIMPLE)
            
            
            assert len(points) == 1
            points = points[0]
            
            # simplify the curve
            epsilon = 0.02*cv2.arcLength(points, True)
            points = cv2.approxPolyDP(points, epsilon, True)
            points = points[:, 0, :]

            # identify points that are free to be modified in the fitting
            free_points = np.ones(len(points), np.bool)
            roi_h, roi_w = mask.shape
            for k, p in enumerate(points):
                if p[0] == 1 or p[1] == 1 or p[0] == roi_w - 2 or p[1] == roi_h - 2:
                    free_points[k] = False
                    
            
            burrow = Burrow(points, image=frame_roi)
            outline = self.refine_burrow_outline(burrow, free_points)
            
            outline = [(p[0] + rect[0], p[1] + rect[1])
                       for p in outline]
            
            burrows.append(Burrow(outline, time=frame_id))
            
        return burrows
                         

class Burrow(object):
    """ represents a single burrow to compare it against an image in fitting """
    
    array_columns = ['Time', 'Position X', 'Position Y']
    index_columns = 0 #< there could be multiple burrows at each time point
    # Hence, time can not be used as an index
    
    def __init__(self, outline, time=None, image=None):
        """ initialize the structure
        size is half the width of the region of interest
        profile_width determines the blurriness of the ridge
        """
        self.outline = outline
        self.image = image
        self.time = time

        
    def __len__(self):
        return len(self.outline)
        
        
    def get_centerline(self):
        raise NotImplementedError
    
        
    def adjust_outline(self, deviations):
        """ adjust the current outline by moving points perpendicular by
        a distance given by `deviations` """
        pass
    
        
    def get_difference(self, deviations):
        """ calculates the difference between image and model, when the 
        model is moved by a certain distance in its normal direction """
        raise NotImplementedError 
        
        dist = 1
           
        # apply sigmoidal function
        model = np.tanh(dist/self.width)
     
        return np.ravel(self.image_mean + 1.5*self.image_std*model - self.image)
    
    
    def show_image(self, mark_points):
        # draw burrow
        image = self.image.copy()
        cv2.drawContours(image, np.array([self.outline], np.int), -1, 255, 1)
        for k, p in enumerate(self.outline):
            color = 255 if mark_points[k] else 128
            cv2.circle(image, (int(p[0]), int(p[1])), 3, color, thickness=-1)
        debug.show_image(image)
    
    
    def to_array(self):
        """ converts the internal representation to a single array """
        time_array = np.zeros((len(self.outline), 1), np.int) + self.time
        return np.hstack((time_array, self.outline))


    @classmethod
    def from_array(cls, data):
        data = np.asarray(data)
        return cls(outline=data[1:, :], time=data[0, 0])
        
    