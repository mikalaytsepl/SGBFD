import cv2
import numpy as np
import mediapipe as mp

# initialize face mesh
mp_face = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=False
)


# rough approximation of face model
model_points = np.array([
    (0.0,   0.0,   0.0),     # nose tip
    (-30.0, -30.0, -30.0),   # left eye
    (30.0,  -30.0, -30.0),   # right eye
    (-25.0, 30.0,  -30.0),   # left mouth
    (25.0,  30.0,  -30.0),   # right mouth
    (0.0,   65.0,  -30.0)    # chin
], dtype=np.float64)


# estimate how sharp the image is 
def estimate_sharpness(image) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


# getting yaw, pitch and roll of the face 
def get_head_pose(image):

    if image is None:
        return None

    h, w = image.shape[:2]

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    results = mp_face.process(rgb)

    # no face detected
    if not results.multi_face_landmarks:
        return None

    # get landmarks from the face 
    lm = results.multi_face_landmarks[0].landmark


    # check if face is not too small, too small faces are unstable -- so don't include
    face_width = abs(lm[263].x - lm[33].x) * w

    if face_width < 80:
        return None

    # get face points from mediapipe landmarks 
    image_points = np.array([
        (lm[1].x   * w, lm[1].y   * h),   # nose
        (lm[33].x  * w, lm[33].y  * h),   # left eye
        (lm[263].x * w, lm[263].y * h),   # right eye
        (lm[61].x  * w, lm[61].y  * h),   # left mouth
        (lm[291].x * w, lm[291].y * h),   # right mouth
        (lm[152].x * w, lm[152].y * h)    # chin
    ], dtype=np.float64)

    # camera approximation for PnP 
    focal_length = w

    camera_matrix = np.array([
        [focal_length, 0, w / 2],
        [0, focal_length, h / 2],
        [0, 0, 1]
    ], dtype=np.float64)

    # assume no lens distortion
    dist_coeffs = np.zeros((4, 1))

    # Solve PerspectiveNPoint
    # finds rotation of the 3d model relative to camera.

    success, rvec, tvec = cv2.solvePnP(
        model_points,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return None

    # convert vector to matrix 
    rmat, _ = cv2.Rodrigues(rvec)

    # euler extraction
    sy = np.sqrt(rmat[0, 0]**2 + rmat[1, 0]**2)

    # singularity check
    if sy < 1e-6:
        return None

    # get deviatoin from the approximation in degrees 
    pitch = np.arctan2(rmat[2, 1], rmat[2, 2])
    yaw   = np.arctan2(-rmat[2, 0], sy)
    roll  = np.arctan2(rmat[1, 0], rmat[0, 0])

    pitch, yaw, roll = np.degrees([pitch, yaw, roll])

    return yaw, pitch, roll


# scoring part 
def get_frontality(
    image,
    max_deviation=20,
    blur_weight=0.01 # not defining blur weith and setting is as is every time, might check later
):

    pose = get_head_pose(image)

    if pose is None:
        return None

    yaw, pitch, roll = pose

    # hard rejection if outside of max deviation threshold
    if (
        abs(yaw) > max_deviation or
        abs(pitch) > max_deviation or
        abs(roll) > max_deviation
    ):
        return None

    # weighted pose score 
    pose_score = (
        abs(yaw)   * 1.5 +
        abs(pitch) * 1.0 +
        abs(roll)  * 0.8
    )

    # blur penaly -- sharper images are more preferred
    sharpness = estimate_sharpness(image)

    blur_penalty = 1 / (sharpness + 1e-6)

    final_score = pose_score + blur_penalty * blur_weight

    # return that package -- lowest score wins
    return {
        "yaw": yaw,
        "pitch": pitch,
        "roll": roll,
        "sharpness": sharpness,
        "score": final_score
    }

def is_frontal(image, max_deviation=10):

    result = get_frontality(image, max_deviation)

    return result is not None

if __name__ == "__main__":

    img = cv2.imread(
        "/home/miko/diploma_thing/Datasets/VGGFace2/n000487/0003_01.jpg"
    )

    if img is None:
        print("Failed to load image")
        exit()

    result = get_frontality(img, max_deviation=20)

    if result is None:
        print("Image rejected")
    else:
        print("\n===== FRONT FACE ANALYSIS =====")
        print(f"Yaw:       {result['yaw']:.2f}")
        print(f"Pitch:     {result['pitch']:.2f}")
        print(f"Roll:      {result['roll']:.2f}")
        print(f"Sharpness: {result['sharpness']:.2f}")
        print(f"Score:     {result['score']:.4f}")

        if is_frontal(img, 10):
            print("\nFrontal face")
        else:
            print("\nNot frontal enough")