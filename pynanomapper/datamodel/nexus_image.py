import h5py
import numpy as np
import cv2
import os
import nexusformat.nexus.tree as nx

#just to store this working demo code
#multiple images with axes
def test_image(root,images = ["demo_cu","demo_zr","demo_ag","demo_al"]):
    # Create a new Nexus file
    nexus_file = nx.NXroot()
    #nx.nxload("my_image.nexus", "w")
    # Create a group to store image data
    entry = nx.NXentry()
    entry["instrument"] = nx.NXinstrument()
    entry["instrument"]["detector"] = nx.NXdetector()

    size = {
        "demo_cu" : [5,5],
        "demo_zr" : [10,10],
        "demo_ag" : [3,3],
        "demo_al" : [6.5,6.5]
    }

    for imgfile in images:
        image_file = os.path.join(root,imgfile + ".png")  # Replace with the path to your image file
        image_data = cv2.imread(image_file, cv2.IMREAD_GRAYSCALE)  # Assuming grayscale image
        image_data = cv2.flip(image_data, 0)
        print(image_file)
        # Physical dimensions of the object being imaged in millimeters
        object_width = size[imgfile][0]  # Width of the object in mm
        object_height = size[imgfile][1]  # Height of the object in mm

        # Create Nexus axes for X and Y
        x_axis = nx.NXfield(np.linspace(0, object_width, image_data.shape[1]), name="x")
        x_axis.attrs["units"] = "um"

        y_axis = nx.NXfield(np.linspace(0, object_height, image_data.shape[0]), name="y")
        y_axis.attrs["units"] = "um"

        # Specify the axes attribute within the data dataset
        # Create a dataset to store the image data
        data = nx.NXdata(data=image_data, axes=[y_axis,x_axis],name=imgfile)
        entry["instrument"]["detector"][imgfile] = data
        entry["instrument"]["detector"][imgfile].attrs["default"] = "data"

        data.attrs["interpretation"] = "image"
        data.attrs["signal"] = "data"

    # Add groups and datasets to the Nexus file
    nexus_file["entry"] = entry

    # Save the Nexus file
    nexus_file.save("my_nexus.nxs",mode="w")

    # Close the Nexus file when you're done (optional)
    nexus_file.close()
