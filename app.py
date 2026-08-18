import streamlit as st
import re
import base64
import io

from google import genai
from PIL import Image


st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Video Studio")
st.caption("Kontrollü AI video üretim paneli")


# -------------------------------------------------
# GEMINI
# -------------------------------------------------

try:
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    client = None


# -------------------------------------------------
# KANAL PROFİLLERİ
# -------------------------------------------------

CHANNEL_PROFILES = {

    "Başka Bir Hayat": """
Create a clean 2D cartoon editorial illustration for a Turkish YouTube story video.

STRICT CHANNEL VISUAL IDENTITY:

- simple clean 2D cartoon illustration
- bold, clean dark outlines around characters and important objects
- simplified rounded human proportions
- rounded heads and simple facial geometry
- small simple black dot eyes
- minimal nose and mouth details
- flat matte colors
- very subtle simple shading only
- low saturation color palette
- beige, muted brown, taupe, gray and charcoal tones
- clean and uncluttered environments
- simple background architecture and furniture
- visually readable composition
- horizontal YouTube composition
- 16:9 aspect ratio

CHARACTER CONSISTENCY:

When the recurring main male character appears, keep exactly the same
recognizable character design throughout the entire story.

The main character should have:
- rounded head
- simple cartoon facial features
- small black dot eyes
- prominent simple ears
- simplified body proportions
- clean dark outlines
- the same face shape and visual identity in every scene

His clothing, hairstyle, accessories, age appearance and condition may
change ONLY when required by the story, but he must remain clearly
recognizable as the same person.

VISUAL STORYTELLING:

Illustrate the exact narration moment as one clear scene.
Show the character's action, environment and emotional state visually.
Use body language and composition instead of excessive facial detail.

Each image should feel like another frame from the SAME animated
illustrated story.

STRICTLY AVOID:

- photorealism
- realistic photography
- cinematic photography
- realistic human skin
- detailed skin texture
- realistic facial anatomy
- 3D rendering
- Pixar style
- anime or manga style
- graphic novel realism
- painterly illustration
- hyper-detailed environments
- dramatic cinematic color grading
- glossy surfaces
- excessive textures
- vivid saturated colors
- complex lighting effects
- text
- captions
- subtitles
- logos
- watermarks

The result must look like a simple, consistent 2D illustrated cartoon
story, not a photograph and not a realistic digital painting.
""",

    "Sessiz Düzen": """
Create a premium Japanese lifestyle editorial illustration.

VISUAL IDENTITY:
- elegant 2D editorial illustration
- mature Japanese woman approximately 35-40 years old when required
- warm beige
- soft ivory
- natural pale oak
- muted sage green
- low saturation
- gentle natural morning light
- calm minimalist Japanese interior aesthetic
- simple cinematic composition
- one clear scene only
- no irrelevant decorative objects
- no vivid colors
- no strong orange or yellow cast
- no text, captions, logos or watermarks
- horizontal 16:9 YouTube composition

CHARACTER CONSISTENCY:
If a reference character image is supplied,
preserve the same woman's face, age, hairstyle and proportions.
"""
}


# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------

defaults = {
    "sentences": [],
    "images": {},
    "prompts": {},
    "approved": {},
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -------------------------------------------------
# IMAGE HELPER
# -------------------------------------------------

def pil_to_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


# -------------------------------------------------
# GÖRSEL ÜRET
# -------------------------------------------------

def generate_image(
    scene_text,
    channel_name,
    scene_number,
    reference_image=None
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı. "
            "Streamlit Secrets içindeki GEMINI_API_KEY değerini kontrol et."
        )

    profile = CHANNEL_PROFILES[channel_name]

    prompt = f"""
{profile}

SCENE NUMBER:
{scene_number:03}

NARRATION:
"{scene_text}"

SCENE INSTRUCTION:
Create exactly one visual scene representing this narration.

Rules:
- Show only the moment described by the narration.
- Do not place the narration as written text inside the image.
- Do not add subtitles.
- Do not invent unrelated objects or events.
- Maintain visual continuity with the previous and following scenes.
- Use a composition suitable for slow zoom or pan in a YouTube video.
- Keep important subjects away from extreme frame edges.
- Produce a cinematic horizontal 16:9 frame.

If a reference character image is provided:
THE REFERENCE IMAGE DEFINES THE MAIN CHARACTER'S IDENTITY.
Do not redesign the person's face.
Do not replace the person with a similar-looking stranger.
Preserve identity even if camera angle, emotion, clothing or location changes.
"""

    input_content = [prompt]

    if reference_image is not None:

        ref_bytes = pil_to_bytes(reference_image)

        input_content.append(
            genai.types.Part.from_bytes(
                data=ref_bytes,
                mime_type="image/jpeg"
            )
        )

    interaction = client.interactions.create(
        model="gemini-3.1-flash-lite-image",
        input=input_content,
        response_format={
            "type": "image",
            "mime_type": "image/jpeg",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )

    if not interaction.output_image:
        raise RuntimeError(
            "Gemini görsel döndürmedi."
        )

    image_bytes = base64.b64decode(
        interaction.output_image.data
    )

    image = Image.open(
        io.BytesIO(image_bytes)
    )

    return image, prompt


# -------------------------------------------------
# KANAL
# -------------------------------------------------

channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen"
    ]
)


# -------------------------------------------------
# REFERANS KARAKTER
# -------------------------------------------------

st.subheader("🎭 Karakter Referansı")

reference_file = st.file_uploader(
    "Ana karakterin referans görselini yükle",
    type=["jpg", "jpeg", "png"],
    help=(
        "Bu görsel tüm sahnelerde ana karakterin kimliğini "
        "korumak için kullanılacak."
    )
)

reference_image = None

if reference_file is not None:

    reference_image = Image.open(
        reference_file
    ).convert("RGB")

    col_ref1, col_ref2 = st.columns([1, 3])

    with col_ref1:

        st.image(
            reference_image,
            caption="Karakter Referansı",
            use_container_width=True
        )

    with col_ref2:

        st.success(
            "Referans karakter yüklendi. "
            "Yeni üretilen sahnelerde bu kimlik korunmaya çalışılacak."
        )

else:

    if channel == "Başka Bir Hayat":

        st.warning(
            "Başka Bir Hayat için karakter referansı yüklemeni öneriyorum. "
            "Referans olmadan karakter yüzü sahneler arasında değişebilir."
        )


st.divider()


# -------------------------------------------------
# METİN
# -------------------------------------------------

st.subheader("1. Video Metni")

script = st.text_area(
    "Video metnini buraya yapıştır",
    height=300,
    placeholder="Hazırladığımız video metnini buraya yapıştır..."
)

if st.button(
    "Metni Cümlelere Ayır",
    type="primary"
):

    if not script.strip():

        st.warning(
            "Önce video metnini gir."
        )

    else:

        sentences = re.split(
            r'(?<=[.!?])\s+',
            script.strip()
        )

        sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

        st.session_state["sentences"] = sentences
        st.session_state["images"] = {}
        st.session_state["prompts"] = {}
        st.session_state["approved"] = {}


# -------------------------------------------------
# SAHNELER
# -------------------------------------------------

if st.session_state["sentences"]:

    sentences = st.session_state["sentences"]

    approved_count = sum(
        1
        for value in st.session_state["approved"].values()
        if value
    )

    st.success(
        f"Metin hazır: {len(sentences)} sahne bulundu."
    )

    st.progress(
        approved_count / len(sentences)
        if sentences
        else 0
    )

    st.caption(
        f"Onaylanan: {approved_count} / {len(sentences)}"
    )

    st.subheader("2. İlk 20 Sahne")

    for index, sentence in enumerate(
        sentences[:20],
        start=1
    ):

        with st.container(border=True):

            status = (
                "✅"
                if st.session_state["approved"].get(index)
                else "⏳"
            )

            st.markdown(
                f"### {status} Sahne {index:03}"
            )

            st.write(sentence)

            if index in st.session_state["images"]:

                st.image(
                    st.session_state["images"][index],
                    use_container_width=True
                )

            col1, col2, col3 = st.columns(3)

            with col1:

                button_text = (
                    "🔄 Yeniden Üret"
                    if index in st.session_state["images"]
                    else "🎨 Görsel Üret"
                )

                if st.button(
                    button_text,
                    key=f"generate_{index}",
                    use_container_width=True
                ):

                    with st.spinner(
                        f"Sahne {index:03} hazırlanıyor..."
                    ):

                        try:

                            image, prompt = generate_image(
                                scene_text=sentence,
                                channel_name=channel,
                                scene_number=index,
                                reference_image=reference_image
                            )

                            st.session_state["images"][index] = image
                            st.session_state["prompts"][index] = prompt
                            st.session_state["approved"][index] = False

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Görsel üretilemedi: {e}"
                            )

            with col2:

                if index in st.session_state["images"]:

                    approve_label = (
                        "✅ Onaylandı"
                        if st.session_state["approved"].get(index)
                        else "✓ Onayla"
                    )

                    if st.button(
                        approve_label,
                        key=f"approve_{index}",
                        use_container_width=True,
                        disabled=st.session_state["approved"].get(
                            index,
                            False
                        )
                    ):

                        st.session_state["approved"][index] = True
                        st.rerun()

            with col3:

                if index in st.session_state["prompts"]:

                    with st.expander(
                        "✏️ Prompt"
                    ):

                        st.text_area(
                            "Kullanılan prompt",
                            st.session_state["prompts"][index],
                            height=250,
                            key=f"prompt_view_{index}"
                        )

    if len(sentences) > 20:

        st.info(
            f"Şimdilik ilk 20 sahne gösteriliyor. "
            f"Toplam {len(sentences)} sahne var."
        )
