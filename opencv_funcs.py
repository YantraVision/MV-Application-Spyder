import cv2

def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    # return the resized image
    return resized

def do_blob_detection(imgTmp):
    
    # blob detection code comes here:
    contours, hierarchy = cv2.findContours(image = imgTmp, mode = cv2.RETR_EXTERNAL, method = cv2.CHAIN_APPROX_SIMPLE)
    
    # draw contours:
    cv2.drawContours(image = imgTmp, contours = contours, contourIdx = -1, color = (0, 0, 255), thickness = 5)
    
    return contours, imgTmp

def do_threshold(imgTmp, low_th, upp_th, do_invert = False):
    
    if isinstance(imgTmp, str):
        imgTmp = cv2.imread(imgTmp, cv2.IMREAD_UNCHANGED)
    
    # if image is not grayscale, make it grayscale:
    if len(imgTmp.shape) == 3:
        imgTmp = cv2.cvtColor(imgTmp, cv2.COLOR_BGR2GRAY)
    
    # do threshold processing:
    if do_invert == False:
        (t, imgTmp) = cv2.threshold(src = imgTmp, thresh = low_th, maxval = 255, type = cv2.THRESH_TOZERO)
        (t, imgTmp) = cv2.threshold(src = imgTmp, thresh = upp_th, maxval = 255, type = cv2.THRESH_BINARY)
    else:
        (t, imgTmp) = cv2.threshold(src = imgTmp, thresh = low_th, maxval = 255, type = cv2.THRESH_TOZERO_INV)
        (t, imgTmp) = cv2.threshold(src = imgTmp, thresh = upp_th, maxval = 255, type = cv2.THRESH_BINARY_INV)
        
    return imgTmp
    
def do_color_conversion(imgTmp, ch_r, ch_g, ch_b, do_grayscale = False, do_bgrtorgb = False):
    
    if isinstance(imgTmp, str):
        imgTmp = cv2.imread(imgTmp, cv2.IMREAD_UNCHANGED)
    
    # if RGB channels are there, do slider value processing:
    if len(imgTmp.shape) == 3:
        # Multiply with R Channel:
        imgTmp[:,:,2] = imgTmp[:,:,2] * ch_r
        # Multiply with G Channel:
        imgTmp[:,:,1] = imgTmp[:,:,1] * ch_g
        # Multiply with B Channel:
        imgTmp[:,:,0] = imgTmp[:,:,0] * ch_b
    
    if len(imgTmp.shape) < 3:
        do_grayscale = False
    
    if do_grayscale == True:
        imgTmp = cv2.cvtColor(imgTmp, cv2.COLOR_BGR2GRAY)
    
    # if do_bgrtorgb is True, convert to RGB:
    if do_bgrtorgb == True and len(imgTmp.shape) == 3:
        imgTmp = cv2.cvtColor(imgTmp, cv2.COLOR_BGR2RGB)
    
    return imgTmp