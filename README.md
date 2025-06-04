# roboflow-posture-test
Test using roboflow to analyze the posture of someone while working in front of camera.

## Objective
The objective is to alert the user when its posture is not good while working. To achieve this,the roboflow universe model https://universe.roboflow.com/posturecorrection/posture_correction_v4/model/1 was used.

## Examples
Some examples of good and bad postures.

![Not good!](https://github.com/user-attachments/assets/c3477dc4-589b-4021-b574-53f34977ed8c)

![Not good!](https://github.com/user-attachments/assets/e17b2cf6-2f7a-43a2-869f-4b66b9ab2e97)

![Good!](https://github.com/user-attachments/assets/67334b32-1d01-4876-9b90-efed39be9f74)

## Next steps
The core functionality is done. 
 Usability improvements:
 - higher sound alert
 - UI for configurations (sound alert enable/disable, view/disable image, time with bad posture for alerts)
Model improvements:
- train the model for images on the side of the person (dual monitor setup)
- It can be even more useful, if there is a camera on the side filming the whole body and column position. And we can train the model with images on this.
- If the model with mixed kinds of images does not perform well, we can make a two step approach (position of camera and then choosing a specialized model for each one)

