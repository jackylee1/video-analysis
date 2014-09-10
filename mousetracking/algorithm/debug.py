'''
Created on Aug 8, 2014

@author: zwicker

module that contains several functions useful when debugging the algorithm
'''

from __future__ import division

import itertools

import numpy as np
from mpl_toolkits.axes_grid1 import make_axes_locatable  # @UnresolvedImport

__all__ = ['show_image', 'show_shape', 'print_filter_chain']


def show_image(*images, **kwargs):
    """ shows a collection of images using matplotlib and waits for the user to continue """
    import matplotlib.pyplot as plt

    # determine the number of rows and columns to show
    num_plots = len(images)
    if num_plots <= 2:
        num_rows = 1
    elif num_plots <= 6:
        num_rows = 2
    else:
        num_rows = 3
    num_cols = int(np.ceil(num_plots/num_rows))
    
    # get the color scale
    if kwargs.pop('equalize_colors', False):
        vmin, vmax = np.inf, -np.inf
        for image in images:
            vmin = min(vmin, image.min())    
            vmax = max(vmax, image.max())
    else:
        vmin, vmax = None, None    
    
    # plot all the images
    for k, image in enumerate(images):
        plt.subplot(num_rows, num_cols, k + 1)
        plt.imshow(image, interpolation='nearest', vmin=vmin, vmax=vmax)
        plt.gray()
        
        if image.min() != image.max():
            # recipe from http://stackoverflow.com/a/18195921/932593
            divider = make_axes_locatable(plt.gca())
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(cax=cax)
        
    # show the images and wait for user input
    plt.show()
    if kwargs.get('wait_for_key', True):
        raw_input('Press enter to continue...')
    
    
    
def show_shape(*shapes, **kwargs):
    """ plots several shapes """
    import matplotlib.pyplot as plt
    import shapely.geometry as geometry
    import descartes
    
    background = kwargs.get('background', None)
    wait_for_key = kwargs.get('wait_for_key', True)
    mark_points = kwargs.get('mark_points', False)
    
    # set up the plotting
    plt.figure()
    ax = plt.gca()
    colors = itertools.cycle('b g r c m y k'.split(' '))
    
    # plot background, if applicable
    if background is not None:
        axim = ax.imshow(background, origin='upper',
                         interpolation='nearest', cmap=plt.get_cmap('gray'))
        if background.min() != background.max():
            # recipe from http://stackoverflow.com/a/18195921/932593
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="5%", pad=0.05)
            plt.colorbar(axim, cax=cax)
    
    # iterate through all shapes and plot them
    for shape in shapes:
        color = kwargs.get('color', colors.next())
        line_width = kwargs.get('lw', 3)
        
        if isinstance(shape, geometry.Polygon):
            patch = descartes.PolygonPatch(shape,
                                           ec=kwargs.get('ec', 'none'),
                                           fc=color, alpha=0.5)
            ax.add_patch(patch)
            if mark_points:
                ax.plot(shape.xy[0], shape.xy[1], 'o', markersize=2*line_width, color=color)
            
        elif isinstance(shape, geometry.LineString):
            ax.plot(shape.xy[0], shape.xy[1], color=color, lw=line_width)
            if mark_points:
                ax.plot(shape.xy[0], shape.xy[1], 'o', markersize=2*line_width, color=color)
            
        elif isinstance(shape, geometry.multilinestring.MultiLineString):
            for line in shape:
                ax.plot(line.xy[0], line.xy[1], color=color, lw=line_width)
                if mark_points:
                    ax.plot(line.xy[0], line.xy[1], 'o', markersize=2*line_width, color=color)
            
        else:
            raise ValueError("Don't know how to plot %r" % shape)
        
    # adjust image axes
    if background is None:
        ax.invert_yaxis()
        ax.margins(0.1)
        ax.autoscale_view(tight=False, scalex=True, scaley=True)
    else:
        ax.set_xlim(0, background.shape[1])
        ax.set_ylim(background.shape[0], 0)
    
    plt.show()
    if wait_for_key:
        raw_input('Press enter to continue...')
           

    
def show_tracking_graph(graph, path, **kwargs):
    """ displays a representation of the tracking graph """
    import matplotlib.pyplot as plt
    
    # plot the known chunks
    for node in graph.nodes():
        plt.plot([node.start, node.end],
                 [node.first.pos[0], node.last.pos[0]],
                 'r', lw=(1 + 10*node.mouse_score))
        
    try:
        max_weight = max(data['weight'] for _, _, data in graph.edges_iter(data=True))
    except ValueError:
        max_weight = 1
    
    if kwargs.get('plot_edges', False):
        for (a, b, d) in graph.edges_iter(data=True):
            plt.plot([a.end, b.start],
                     [a.last.pos[0], b.first.pos[0]],
                     color=str(d['weight']/max_weight), lw=1)
        
    # plot the actual graph
    node_prev = None
    for node in path:
        plt.plot([node.start, node.end],
                 [node.first.pos[0], node.last.pos[0]],
                 'b', lw=2)
        if node_prev is not None:
            plt.plot([node_prev.end, node.start],
                     [node_prev.last.pos[0], node.first.pos[0]],
                     'b', lw=2)
        node_prev = node

    # show plot
    plt.xlabel('Time in Frames')
    plt.ylabel('X Position')
    plt.margins(0, 0.1)
    plt.show()
    if kwargs.get('wait_for_key', True):
        raw_input('Press enter to continue...')


    
def print_filter_chain(video):
    """ prints information about a filter chain """
    # print statistics of current video
    print(str(video))
    
    # go up one level
    try:
        print_filter_chain(video._source)
    except AttributeError:
        pass
    
    
    
def save_frame_from_video(video, outfile):
    """ save the next video frame to outfile """
    # get frame
    pos = video.get_frame_pos()
    frame = video.next()
    video.set_frame_pos(pos)
    
    # turn it into image
    from PIL import Image  # @UnresolvedImport
    im = Image.fromarray(frame)
    im.save(outfile)
    