# MorDIFF Pipeline Overview

This notebook builds a full face-morphing pipeline for a dataset stored in Google Drive. The pipeline has five main stages:

1. Mount the Drive and define the dataset paths.
2. Install the required Python and OS dependencies.
3. Align every face in the raw dataset to a consistent frontal view.
4. Generate a CSV of promising face pairs to morph.
5. Use a DiffAE model to generate morphs between the selected image pairs and save them into a dataset-specific output folder.

The goal is to take a large set of raw images, align them, pick visually similar but distinct identities, and generate a morph sequence that can later be used for analysis, evaluation, or augmentation.

---

## 1. High-level pipeline

At a conceptual level, the notebook does the following:

- Reads all files under a dataset folder.
- Detects and aligns faces using Dlib landmark detection.
- Extracts face embeddings with a FaceNet-based encoder.
- Finds pairs of different identities that are close enough in embedding space to be good morph candidates.
- Saves those candidate pairs to a CSV file like `morph_guidelines.csv`.
- Loads a pretrained DiffAE model.
- Interpolates latent representations between each pair.
- Generates a final morph image and stores it in a dedicated output folder.

This is a typical “pair selection + latent morphing” pipeline.

---

## 2. File and folder layout used by the notebook

The code assumes a Google Drive structure similar to:

```text
/content/drive/MyDrive/
├── Datasets/
│   └── filtered_dataset_ferret_3/
├── Datasets_aligned/
│   └── filtered_dataset_ferret_3/
├── Morph_guidelines/
│   └── filtered_dataset_ferret_3/
│       └── morph_guidelines.csv
├── Morphs/
│   └── filtered_dataset_ferret_3/
│       └── morphed_..._and_....png
└── MorDIFF/
```

The notebook defines:

```python
DATASET_PATH = "/content/drive/MyDrive/Datasets/filtered_dataset_ferret_3"
DATASET_NAME = DATASET_PATH.split('/')[-1]
ALIGNED_PATH = "/content/drive/MyDrive/Datasets_aligned"
```

This means the dataset name is derived from the last path segment, for example:

- `filtered_dataset_ferret_3`

That dataset name is then reused in the output locations for aligned images, guidelines, and morph results.

---

## 3. Step 1: mount Google Drive and set dataset variables

The first cells are simple setup cells:

```python
from google.colab import drive
drive.mount('/content/drive')
```

and:

```python
%cd /content/drive/MyDrive/MorDIFF
```

These make the notebook work inside Google Colab and ensure the project files live in the mounted Drive. This is necessary because the dataset, checkpoint, and output files are all stored in Drive rather than the local runtime filesystem.

The dataset variables are then created:

```python
DATASET_PATH = "/content/drive/MyDrive/Datasets/filtered_dataset_ferret_3"
DATASET_NAME = DATASET_PATH.split('/')[-1]
ALIGNED_PATH = "/content/drive/MyDrive/Datasets_aligned"
```

### Syntax breakdown

- `DATASET_PATH` = source folder containing original images.
- `DATASET_NAME` = dataset name derived from the last path component.
- `ALIGNED_PATH` = root directory that will hold aligned output images.

This pattern allows the code to reuse the same dataset name in all downstream folders without hardcoding a different value each time.

---

## 4. Step 2: install dependencies

This block installs the libraries required for:

- face detection and landmark extraction (`dlib`)
- image processing (`Pillow`, `scipy`, `opencv`)
- deep learning (`torch`, `torchvision`, `pytorch-lightning`)
- embeddings and perceptual metrics (`facenet-pytorch`, `lpips`)
- CSV and dataframe processing (`pandas`)
- progress output (`tqdm`)

```bash
%%bash
set -e
apt-get update -qq
apt-get install -y -qq cmake build-essential libgl1 libglib2.0-0
python -m pip install --quiet --upgrade pip
pip install -q \
  dlib-bin \
  "pytorch-lightning<2.0" \
  pytorch-fid \
  lpips \
  lmdb \
  facenet-pytorch \
  numpy \
  scipy \
  pillow \
  requests \
  tqdm \
  matplotlib \
  pandas \
  scikit-image \
  opencv-python-headless \
  torchvision
```

### Why this matters

The notebook uses several libraries that are not always installed in Colab by default. Without `dlib`, `facenet-pytorch`, and the image libraries, the pipeline cannot:

- detect faces,
- align them,
- compute embeddings,
- or render morphs.

The final block then checks whether the required imports are available:

```python
import importlib
mods = [
    'torch', 'torchvision', 'PIL', 'numpy', 'scipy', 'requests', 'tqdm',
    'matplotlib', 'skimage', 'cv2', 'dlib', 'facenet_pytorch', 'lpips', 'lmdb'
]
```

This is a safety check to fail early if any dependency is still missing.

---

## 5. Step 3: align the dataset

This is the first major computational stage. The notebook uses Dlib’s face detector and landmark predictor to normalize faces into a standard frontal pose.

### Core function: `get_shape_predictor()`

```python
def get_shape_predictor():
    url = 'http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2'
    bz2_path = 'temp/shape_predictor_68_face_landmarks.dat.bz2'
    dat_path = 'temp/shape_predictor_68_face_landmarks.dat'

    if os.path.exists(dat_path):
        return dat_path

    os.makedirs('temp', exist_ok=True)
    if not os.path.exists(bz2_path):
        print("Downloading dlib 68-face landmarks model...")
        response = requests.get(url, stream=True)
        with open(bz2_path, 'wb') as f:
            f.write(response.content)

    print("Decompressing landmarks model...")
    with open(dat_path, 'wb') as f_out, bz2.BZ2File(bz2_path, 'rb') as f_in:
        f_out.write(f_in.read())

    return dat_path
```

### What this does

- downloads Dlib’s 68-landmark model
- stores it in a local `temp` folder
- decompresses the `.bz2` archive
- returns the path to the extracted model file

This model is required for detecting eyes, nose, mouth, and face contour.

---

### Core function: `image_align()`

```python
def image_align(src_file, dst_file, face_landmarks, output_size=256, transform_size=4096, enable_padding=True):
```

This function takes a source image and a list of face landmark points, then transforms the face into a normalized front-facing crop.

#### The important idea

The code:

- computes the center between the eyes,
- estimates the eye-to-mouth axis,
- creates a geometric quadrilateral around the face,
- warps the image so the eyes are aligned in a consistent position,
- crops and pads the image to reduce distortion.

This is a face normalization step. Without it, the morph model would be comparing faces in slightly different angles or positions, which is a major source of poor morph quality.

Key operations include:

```python
lm_eye_left = lm[36:42]
lm_eye_right = lm[42:48]
... 
quad = np.stack([c - x - y, c - x + y, c + x + y, c + x - y])
```

These compute the transformation points used to warp the image into a frontalized face.

Finally:

```python
img = img.transform((transform_size, transform_size), PIL.Image.QUAD, (quad + 0.5).flatten(), PIL.Image.BILINEAR)
if output_size < transform_size:
    img = img.resize((output_size, output_size), PIL.Image.LANCZOS)

img.save(dst_file, 'PNG')
```

This writes the aligned face to disk as a PNG file.

---

### Core function: `align_dataset()`

```python
def align_dataset(input_root, output_root):
    model_path = get_shape_predictor()
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(model_path)
```

This walks through every image in the dataset directory, detects faces, and saves aligned versions in the new output directory.

```python
for ext in extensions:
    image_paths.extend(glob.glob(os.path.join(input_root, '**', ext), recursive=True))
```

This is recursive file discovery: it searches all subfolders, not just the top level.

Then each image is processed:

```python
img = dlib.load_rgb_image(img_path)
dets = detector(img, 1)
if len(dets) == 0:
    continue

landmarks = [(p.x, p.y) for p in predictor(img, dets[0]).parts()]
image_align(img_path, out_path, landmarks, output_size=256)
```

### What this produces

The notebook saves aligned images into:

```python
output_root=f"{ALIGNED_PATH}/{DATASET_NAME}"
```

So the aligned dataset is kept in a versioned, dataset-specific folder, preserving the original folder structure.

---

## 6. Step 4: generate guideline pairs for morphing

Once aligned images exist, the code creates a list of “good candidate pairs” to morph. This is not just random pairing; it uses embedding similarity to pick faces that are close enough to be visually compatible but different enough to produce a meaningful transformation.

### Why this step exists

A morph is best when the two images are similar in structure, lighting, and pose. The model works much better if:

- the face is already aligned,
- the identities are distinct but visually similar,
- the images are not from the same person.

The notebook solves this by computing face embeddings and measuring cosine similarity.

---

### Embedding generation

```python
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

transform = transforms.Compose([
    transforms.Resize((160, 160)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
])
```

This loads a pretrained FaceNet/Inception-ResNet model trained on VGGFace2. The model converts each face image into a feature vector.

Then each aligned image is processed:

```python
img = Image.open(f).convert('RGB')
tensor = transform(img).unsqueeze(0).to(device)
emb = resnet(tensor).cpu().numpy().flatten()
```

This gives a vector representation of the face.

The vector is normalized:

```python
norm = np.linalg.norm(emb)
if norm > 0:
    emb = emb / norm
```

This is L2 normalization, which makes the comparison based on direction rather than scale. That is important for cosine similarity.

---

### Subject ID extraction

The notebook tracks identity labels using the folder name:

```python
subject_id = os.path.basename(os.path.dirname(f))
if not subject_id or subject_id == os.path.basename(aligned_dir):
    subject_id = os.path.basename(f).split('_')[0]
```

This means it tries to infer the person ID from the folder structure. This is crucial because it avoids pairing images from the same identity together.

---

### Similarity matrix

```python
similarity_matrix = np.dot(embeddings, embeddings.T)
```

This creates a matrix where each entry is the cosine similarity between two face embeddings.

The code then masks out same-subject comparisons:

```python
same_identity_mask = subject_ids[:, None] == subject_ids[None, :]
similarity_matrix[same_identity_mask] = -1.0
```

This ensures that matching a face with another image of the same person is ignored.

---

### Pair selection logic

```python
for i in range(len(valid_files)):
    current_id = subject_ids[i]
    if current_id in used_subject_ids:
        continue

    scores = similarity_matrix[i].copy()

    for used_id in used_subject_ids:
        scores[subject_ids == used_id] = -1.0

    best_match_idx = int(np.argmax(scores))
    sim_score = scores[best_match_idx]
    best_id = subject_ids[best_match_idx]

    if sim_score >= 0.40 and best_id not in used_subject_ids:
        morph_pairs.append({
            "id1": current_id,
            "id2": best_id,
            "img1": valid_files[i],
            "img2": valid_files[best_match_idx],
            "similarity": float(sim_score)
        })
```

### How to read this

- For each identity, it picks the most similar other identity.
- It ignores images already used.
- It requires the similarity score to be high enough (`>= 0.40`) to be considered a viable morph candidate.
- It saves the selected pair in a CSV.

This creates a guide file that later drives morph generation without trying every possible pair in the dataset.

---

### Output CSV

```python
guideline_dir = f"/content/drive/MyDrive/Morph_guidelines/{DATASET_NAME}"
guideline_path = os.path.join(guideline_dir, "morph_guidelines.csv")
```

and then:

```python
df_pairs = pd.DataFrame(morph_pairs)
df_pairs.to_csv(guideline_path, index=False)
```

This is the final suggestions file. A row usually contains:

```text
id1,id2,img1,img2,similarity
```

That means each row tells you which two aligned images should be morphed together.

---

## 7. Step 5: morph generation with DiffAE

The last stage loads the actual generative model and creates the face transitions.

### Model loading

```python
path_to_diff_model = "./diffae-master"
sys.path.append(path_to_diff_model)
from templates import *
```

This assumes the DiffAE project is in a local folder named `diffae-master`.

Then:

```python
conf = ffhq256_autoenc()
model = LitModel(conf)
state = torch.load(
    f'{path_to_diff_model}/checkpoints/{conf.name}/last.ckpt',
    map_location='cpu',
    weights_only=False
)
model.load_state_dict(state['state_dict'], strict=False)
model.ema_model.eval()
model.ema_model.to(device)
```

This loads the trained diffusion autoencoder checkpoint and places the model on the GPU if available.

---

### Why the model is needed

DiffAE does not simply crossfade pixels. Instead it:

- maps input faces to a latent representation,
- interpolates between latent codes,
- reconstructs a blended image from the interpolated latent vector.

This preserves face structure much better than a naive pixel blend.

---

### `cos_sim()` function

```python
def cos_sim(a, b):
    a = F.normalize(a.view(-1), dim=0)
    b = F.normalize(b.view(-1), dim=0)
    return (a * b).sum()
```

This computes cosine similarity between two flattened vectors. It is used during interpolation to estimate the angle between the two latent states.

The important part is the spherical interpolation logic:

```python
intp = cond[0][None] * (1 - alpha[:, None]) + cond[1][None] * alpha[:, None]
```

This line blends the latent conditions of the two images across a set of alpha values.

The `alpha` values are:

```python
alpha = torch.tensor([0.0, 0.5, 1.0], device=device)
```

This means the notebook generates three interpolation states:

- `0.0` → image 1
- `0.5` → midpoint morph
- `1.0` → image 2

---

### The core batch morph loop

```python
img1 = load_aligned(img1_path).unsqueeze(0).to(device)
img2 = load_aligned(img2_path).unsqueeze(0).to(device)
batch = torch.cat([img1, img2], dim=0)

cond = model.encode(batch)
xT = model.encode_stochastic(batch, cond, T=250)
```

This is the critical block:

- `img1` and `img2` are loaded and normalized.
- They are stacked into a single batch.
- The model encodes both faces together.
- `xT` is a stochastic latent representation used in the diffusion process.

Then the notebook interpolates between the latent states:

```python
intp = cond[0][None] * (1 - alpha[:, None]) + cond[1][None] * alpha[:, None]
```

This creates a set of blended latent vectors between image one and image two.

The next block computes the interpolation across the latent manifold:

```python
theta = torch.arccos(cos_sim(xT[0], xT[1]))
intp_x = (
    torch.sin((1 - alpha[:, None]) * theta) * xT[0].flatten(0, 2)[None] +
    torch.sin(alpha[:, None] * theta) * xT[1].flatten(0, 2)[None]
) / torch.sin(theta)
```

This is a spherical interpolation formula: it blends the two latent codes along the shortest path between them rather than just a linear mix. This often gives smoother, more realistic face morphs.

Then:

```python
pred = model.render(intp_x, intp, T=20)
```

This reconstructs an image from the interpolated code.

And finally:

```python
morph_img = to_pil(pred[1].cpu())
morph_img.save(output_path)
```

This saves the middle morph, which is the actual blend result.

---

## 8. Output naming and preserving source information

The notebook creates a final filename using the source basenames:

```python
name1 = os.path.splitext(os.path.basename(img1_path))[0]
name2 = os.path.splitext(os.path.basename(img2_path))[0]
final_name = f"morphed_{name1}_and_{name2}.png"
output_path = os.path.join(output_root, final_name)
```

This is extremely useful because the output file name tells you exactly which two images were used to create it.

Example:

```text
morphed_00012_and_00491.png
```

This means the morph was generated from the aligned image `00012` and the aligned image `00491`.

That is exactly the right pattern for later traceability.

---

## 9. Output directory pattern

The notebook uses:

```python
output_root = f"/content/drive/MyDrive/Morphs/{DATASET_NAME}"
os.makedirs(output_root, exist_ok=True)
```

So, for a dataset named `filtered_dataset_ferret_3`, the final folder becomes:

```text
/content/drive/MyDrive/Morphs/filtered_dataset_ferret_3/
```

This keeps the results grouped by dataset and prevents mixing morphs from different sources.

---

## 10. Full conceptual summary

The notebook is essentially doing this:

1. Face detection and alignment normalize all input faces.
2. Embedding extraction converts each aligned face into a compact feature vector.
3. Similarity comparison finds pairs of different identities that are close enough to produce a realistic morph.
4. A trained DiffAE model reconstructs intermediate faces from latent interpolation.
5. The result is a set of generated images saved in a clean dataset-specific output folder.

This process is useful for:

- face interpolation analysis,
- identity transition studies,
- dataset augmentation,
- visual comparison of morph quality,
- and generating controlled image blends for downstream tasks.

---

## 11. Important practical notes

### A. The pipeline depends on aligned images

If the aligned dataset folder is empty or not created yet, the morph-generation step cannot work correctly. The order should be:

1. align raw images,
2. generate guideline CSV,
3. create morphs from the CSV.

### B. The CSV controls the morph pairs

The model is not morphing the whole dataset automatically. It morphs only the suggested pairs in `morph_guidelines.csv`.

### C. The output name preserves traceability

The naming convention is essential because it lets you later map a generated image back to its source pair.

### D. The notebook uses a 50% midpoint morph

The code saves `pred[1]`, which corresponds to the midpoint interpolation at `alpha=0.5`. This is typically the most visually meaningful morph image because it balances both identities.

---

## 12. Minimal mental model of the pipeline

If you want the shortest possible explanation:

> The notebook aligns faces, computes face embeddings, picks two visually compatible identities, then uses a diffusion autoencoder to interpolate between their latent representations and save the midpoint morph.

That is the whole pipeline in one sentence.

---

## 13. Recommended output pattern for future use

The notebook is already close to the desired workflow. The output folder structure should be:

```text
Morphs/
└── filtered_dataset_ferret_3/
    ├── morphed_00012_and_00491.png
    ├── morphed_00103_and_00502.png
    └── ...
```

This makes it easy to:

- identify input pair names,
- compare morph quality,
- run dataset-level analysis,
- and avoid mixing results across datasets.

---

## 14. Final takeaway

This notebook is a complete morph-generation workflow:

- detect + align faces,
- generate embedding-based recommendations,
- generate morphed face outputs from those suggestions,
- save everything in a dataset-specific folder with clear traceable names.

That is why it is a useful pipeline for generating controlled face transitions from large image datasets.
