import cv2
import numpy as np

def create_sharp_mask(
    image_path: str,
    masking_range: tuple[int, int],
    target_size=(112, 112),
    collage_output_path: str | None = None,
):
    """Apply a hard frequency mask and optionally save a three-panel demo.

    The returned tensor is suitable for the face-recognition model. If
    ``collage_output_path`` is provided, the saved collage contains the
    original image, the masked log-magnitude DFT, and the reconstruction.
    """
    if len(masking_range) != 2:
        raise ValueError("masking_range must contain exactly two values.")

    if masking_range[0] < 0 or masking_range[1] < masking_range[0]:
        raise ValueError(
            "masking_range must be a non-negative "
            "(min_radius, max_radius) tuple."
        )

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    # img = cv2.resize(img, target_size)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    height, width, _ = img.shape
    center_y, center_x = height // 2, width // 2
    y, x = np.ogrid[:height, :width]
    radius = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

    mask_2d = np.ones((height, width), dtype=np.float32)
    mask_2d[
        (radius >= masking_range[0])
        & (radius <= masking_range[1])
    ] = 0.0

    reconstructed_channels = []
    for channel in cv2.split(np.float32(img)):
        dft = cv2.dft(channel, flags=cv2.DFT_COMPLEX_OUTPUT)
        dft_shift = np.fft.fftshift(dft)
        dft_masked = dft_shift * mask_2d[:, :, np.newaxis]
        dft_ishift = np.fft.ifftshift(dft_masked)
        reconstructed_channel = cv2.idft(
            dft_ishift,
            flags=cv2.DFT_SCALE | cv2.DFT_REAL_OUTPUT,
        )
        reconstructed_channels.append(reconstructed_channel)

    reconstructed_img = cv2.merge(reconstructed_channels)
    reconstructed_img = np.clip(
        reconstructed_img,
        0,
        255,
    ).astype(np.uint8)

    if collage_output_path is not None:
        gray_img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
        gray_dft = cv2.dft(gray_img, flags=cv2.DFT_COMPLEX_OUTPUT)
        gray_dft_shift = np.fft.fftshift(gray_dft)
        masked_gray_dft = gray_dft_shift * mask_2d[:, :, np.newaxis]
        spectrum = cv2.magnitude(
            masked_gray_dft[:, :, 0],
            masked_gray_dft[:, :, 1],
        )
        spectrum = np.log1p(spectrum)
        spectrum = cv2.normalize(
            spectrum,
            None,
            alpha=0,
            beta=255,
            norm_type=cv2.NORM_MINMAX,
        ).astype(np.uint8)
        spectrum = cv2.cvtColor(spectrum, cv2.COLOR_GRAY2RGB)

        panels = [
            cv2.putText(
                panel.copy(),
                label,
                (5, 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            for panel, label in (
                (img, "Original"),
                (spectrum, "Sharp Masked DFT"),
                (reconstructed_img, "Reconstructed"),
            )
        ]
        collage = np.concatenate(panels, axis=1)
        collage_bgr = cv2.cvtColor(collage, cv2.COLOR_RGB2BGR)
        if not cv2.imwrite(collage_output_path, collage_bgr):
            raise OSError(
                f"Could not save masking collage to {collage_output_path}"
            )


create_sharp_mask(
    image_path= "/home/mikalay/diploma_thing/Datasets/filtered_dataset_ferret_3/00002/00002_930831_fa.jpg",
    masking_range=(5, 12),
    collage_output_path="test_collage_sharp.jpg"
)