import base64
import io
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import random
import requests


FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
]


def draw_coordinates(
    image: Image.Image,
    coordinates: tuple[int, int],
) -> None:
    """
    Draw a red dot at the specified coordinates on the image. The image is modified in place.

    Args:
        image (Image.Image): Input image
        coordinates (tuple): Coordinates of the point to draw (x, y)
    """
    draw = ImageDraw.Draw(image)
    x, y = coordinates
    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="blue")


def convert_bbox_xywh_to_xyxy(
    bbox_xywh: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """
    Convert bounding box coordinates from (x, y, w, h) format to (x1, y1, x2, y2) format.

    Args:
        bbox_xywh (tuple): Coordinates of the bounding box in (x, y, w, h) format.
            (x, y) is the top-left corner, and w and h are the width and height.

    Returns:
        tuple: Coordinates of the bounding box in (x1, y1, x2, y2) format.
            (x1, y1) is the top-left corner, and (x2, y2) is the bottom-right corner.
    """
    x, y, w, h = bbox_xywh
    return x, y, x + w, y + h


def random_crop(
    image, safe_box: tuple[float, float, float, float], min_size: int = 334
):
    """Randomly crops an image so that the box is still within the image."""
    image_width, image_height = image.size
    min_x, min_y, max_x, max_y = safe_box
    if min_x < 0 or min_y < 0 or max_x > image_width or max_y > image_height:
        return image, 0, 0
    offset_x = int(random.random() * min(min_x, image_width - min_size))
    offset_y = int(random.random() * min(min_y, image_height - min_size))
    max_x -= offset_x
    max_y -= offset_y
    image_width = random.randint(
        max(min_size, min(round(max_x), image_width - offset_x)),
        max(min_size, image_width - offset_x),
    )
    image_height = random.randint(
        max(min_size, min(round(max_y), image_height - offset_y)),
        max(min_size, image_height - offset_y),
    )
    image = image.crop(
        (offset_x, offset_y, offset_x + image_width, offset_y + image_height)
    )
    return image, offset_x, offset_y


def draw_red_arrow(
    image: Image.Image,
    bbox: tuple[float, float, float, float],
) -> None:
    """
    Draws a red box and an arrow pointing to the box. The image is modified in place.

    Args:
        image (Image.Image): Input image
        bbox (tuple): Coordinates of the bounding box in (x1, y1, x2, y2) format.
            (x1, y1) is the top-left corner, (x2, y2) is the bottom
    """
    width, height = image.size
    bbox = [
        max(0, bbox[0] - 5),
        max(0, bbox[1] - 5),
        min(width, bbox[2] + 5),
        min(height, bbox[3] + 5),
    ]
    draw = ImageDraw.Draw(image)
    draw.rectangle([i + 1 for i in bbox], outline="black", width=3)
    draw.rectangle(bbox, outline="red", width=3)

    # Calculate bounding box center and decide arrow direction
    x1, y1, x2, y2 = bbox
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    if center_x < 0 or center_x > width or center_y < 0 or center_y > height:
        raise ValueError("Invalid center point.")

    # Determine if bbox is in the lower or upper half of the image
    if center_y > height / 2:
        # Bbox in lower half, arrow points upward
        start_point = (center_x, y1 - 100)  # Start point above the bounding box
        end_point = (center_x, y1 - 5)  # End point just outside the bounding box
        arrow_tip = end_point
        arrow_left = (center_x - 10, y1 - 20)
        arrow_right = (center_x + 10, y1 - 20)
    else:
        # Bbox in upper half, arrow points downward
        start_point = (center_x, y2 + 100)  # Start point below the bounding box
        end_point = (center_x, y2 + 5)  # End point just outside the bounding box
        arrow_tip = end_point
        arrow_left = (center_x - 10, y2 + 20)
        arrow_right = (center_x + 10, y2 + 20)

    # Draw shadow first
    shadow_offset = (2, 2)
    draw.line(
        [
            tuple(map(sum, zip(start_point, shadow_offset))),
            tuple(map(sum, zip(end_point, shadow_offset))),
        ],
        fill="black",
        width=2,
    )
    draw.polygon(
        [
            tuple(map(sum, zip(arrow_tip, shadow_offset))),
            tuple(map(sum, zip(arrow_left, shadow_offset))),
            tuple(map(sum, zip(arrow_right, shadow_offset))),
        ],
        fill="black",
    )

    # Draw the red arrow on top of the shadow
    draw.line([start_point, end_point], fill="red", width=2)
    draw.polygon([arrow_tip, arrow_left, arrow_right], fill="red")


def convert_image_to_pil_image(
    image: bytes | str | np.ndarray | Image.Image,
) -> Image.Image:
    """
    Convert an image to a PIL Image.

    Args:
        image (bytes | str | np.ndarray | Image.Image): Image data in one of the following formats:
            - bytes: Image data as bytes
            - str: Base64-encoded image string
            - np.ndarray: NumPy array representing the image
            - Image.Image: PIL image object

    Returns:
        Image.Image: PIL image object
    """
    if isinstance(image, bytes):
        return convert_image_bytes_to_pil_image(image)
    elif isinstance(image, str):
        return base64_to_image(image)
    elif isinstance(image, np.ndarray):
        return Image.fromarray(image)
    elif isinstance(image, Image.Image):
        return image
    else:
        raise ValueError("Unsupported image format.")


def convert_image_bytes_type(
    image_bytes: bytes,
    image_format: str,
) -> bytes:
    """
    Convert an image from one format to another.

    Args:
        image_bytes (bytes): Image data as bytes
        image_format (str): Format of the image (e.g., "JPEG", "PNG")

    Returns:
        bytes: Image data as bytes in the new format
    """
    # Load the image
    image = Image.open(io.BytesIO(image_bytes))

    # Save the image in the new format
    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def save_image_bytes_to_file(
    image_bytes: bytes,
    file_path: str,
    image_format: str | None = None,
) -> None:
    """
    Save image bytes to a file.

    Args:
        image_bytes (bytes): Image data as bytes
        file_path (str): Path to the output file
        image_format (str | None): Format of the image (e.g., "JPEG", "PNG") to be saved as.
            If None, the format is inferred from the file extension.
    """
    image = Image.open(io.BytesIO(image_bytes))
    image.save(file_path, format=image_format)


def convert_pil_image_to_base64_str(
    img: Image.Image,
    image_format: str | None = None,
) -> str:
    """
    Convert a PIL image to a base64-encoded string.

    Args:
        img (Image.Image): PIL image object
        image_format (str | None): Format of the image (e.g., "JPEG", "PNG") to be saved as.
            If None, the format is inferred from the file extension.

    Returns:
        str: Base64-encoded image string
    """
    with io.BytesIO() as f:
        img.convert("RGB").save(f, image_format)
        return base64.b64encode(f.getvalue()).decode("utf-8")


def convert_image_bytes_to_base64_str(
    image_bytes: bytes,
    image_format: str,
) -> str:
    """
    Convert image bytes to a base64-encoded string.

    Args:
        image_bytes (bytes): Image data as bytes
        image_format (str): Format of the image (e.g., "JPEG", "PNG")

    Returns:
        str: Base64-encoded image string
    """
    img = convert_image_bytes_to_pil_image(image_bytes)
    return convert_pil_image_to_base64_str(img, image_format)


def convert_image_bytes_to_pil_image(
    image_bytes: bytes,
) -> Image.Image:
    """
    Convert image bytes to a PIL image.

    Args:
        image_bytes (bytes): Image data as bytes

    Returns:
        Image.Image: PIL image object
    """
    return Image.open(io.BytesIO(image_bytes))


def pil_image_to_bytes(
    image_pil: Image.Image,
    image_format: str,
) -> bytes:
    """
    Converts a PIL Image to a bytes object.
    Args:
        image (PIL.Image.Image): The image to convert.
        format (str): The format in which to save the image (e.g., 'PNG', 'JPEG').
    Returns:
        bytes: The binary representation of the image.
    """
    byte_io = io.BytesIO()
    image_pil.save(byte_io, format=image_format)
    image_bytes = byte_io.getvalue()
    return image_bytes


def calculate_iou_of_bbox(
    box1: tuple[float, float, float, float],
    box2: tuple[float, float, float, float],
) -> float:
    """
    Calculate the Intersection over Union (IoU) between two bounding boxes.

    Args:
    box1 (tuple): Coordinates of the first box in (x1, y1, x2, y2) format.
        (x1, y1) is the top-left corner, (x2, y2) is the bottom-right corner.
    box2 (tuple): Coordinates of the second box in (x1, y1, x2, y2) format.
        (x1, y1) is the top-left corner, (x2, y2) is the bottom-right corner.

    Returns:
    float: The IoU value (between 0 and 1).
    """

    # Extract coordinates of the bounding boxes
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2

    # Calculate the coordinates of the intersection box
    x_inter_min = max(x1_min, x2_min)
    y_inter_min = max(y1_min, y2_min)
    x_inter_max = min(x1_max, x2_max)
    y_inter_max = min(y1_max, y2_max)

    # Compute the area of the intersection box
    inter_width = max(0, x_inter_max - x_inter_min)
    inter_height = max(0, y_inter_max - y_inter_min)
    area_intersection = inter_width * inter_height

    # Compute the area of both the bounding boxes
    area_box1 = (x1_max - x1_min) * (y1_max - y1_min)
    area_box2 = (x2_max - x2_min) * (y2_max - y2_min)

    # Compute the area of union
    area_union = area_box1 + area_box2 - area_intersection

    # Compute the IoU
    iou = area_intersection / area_union if area_union != 0 else 0

    return iou


def numpy_to_base64_bytes(arr):
    img = Image.fromarray(arr, mode="RGB")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue())


def numpy_to_base64(arr):
    return numpy_to_base64_bytes(arr).decode("utf-8")


def base64_to_image(base64_str):
    # Decode base64 string into a PIL Image
    image_data = base64.b64decode(base64_str)

    # Convert the binary data to a PIL Image
    image = convert_image_bytes_to_pil_image(image_data)

    return image


def base64_bytes_to_image(base64_bytes):
    base64_str = base64_bytes.decode("utf-8")
    return base64_to_image(base64_str)


def download_image_as_numpy_array(url):
    response = requests.get(url)
    image = Image.open(io.BytesIO(response.content))
    image = np.asarray(image)
    return image


def download_image_as_base64_str(url):
    response = requests.get(url)
    return base64.b64encode(response.content).decode()


def convert_image_bytes_to_numpy(image_bytes: bytes) -> np.ndarray:
    """
    Convert image bytes to a NumPy array.

    Args:
        image_bytes (bytes): Image data as bytes

    Returns:
        np.ndarray: NumPy array representing the image
    """
    image = convert_image_bytes_to_pil_image(image_bytes)
    return np.array(image)


def convert_pil_image_to_image_bytes(image: Image.Image, image_format: str) -> bytes:
    """
    Convert a PIL image to image bytes.

    Args:
        image (Image.Image): PIL image object
        image_format (str): Format of the image (e.g., "JPEG", "PNG")

    Returns:
        bytes: Image data as bytes
    """
    with io.BytesIO() as f:
        image.save(f, format=image_format)
        return f.getvalue()


class BoxDrawer:
    def __init__(self, draw, size):
        self.order = list(range(4))
        random.shuffle(self.order)
        self.draw = draw
        self.width = random.randint(1, 3)
        self.boxes = []
        self.labels = []
        self.size = size
        self.text_size = random.randint(10, 30)
        self.text_padding = random.randint(0, 3)

    def add_box(self, box, label):
        self.boxes.append(box)
        self.labels.append(label)

    def finalize(self):
        for box in self.boxes:
            self.draw.rectangle(box, outline="red", width=self.width)

        font = ImageFont.truetype(random.choice(FONTS), self.text_size)
        for i, box in enumerate(self.boxes):
            # Calculate text position
            text_box_size = self.text_size + self.text_padding * 2
            box_locations = [
                (box[0], box[1] - text_box_size),  # top left
                (box[0], box[3]),  # bottom left
                (box[2] - text_box_size, box[1] - text_box_size),  # top right
                (box[2] - text_box_size, box[3]),  # bottom right
            ]
            selected_location = (box[0], box[1])
            for j in self.order:
                text_x, text_y = box_locations[j]
                if text_y < 0:
                    continue
                if text_x < 0:
                    continue
                if text_x + text_box_size > self.size[0]:
                    continue
                if text_y + text_box_size > self.size[1]:
                    continue
                selected_location = (text_x, text_y)
                break
            text_x, text_y = selected_location

            # Draw black rectangle for the label background
            self.draw.rectangle(
                [(text_x, text_y), (text_x + text_box_size, text_y + text_box_size)],
                fill="black",
            )

            # Draw the label with white text
            self.draw.text(
                (text_x + self.text_padding, text_y + self.text_padding),
                self.labels[i],
                fill="white",
                font=font,
            )
