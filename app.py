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


# -----------------------------
# GEMINI CLIENT
# -----------------------------
try:
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    client = None


# -----------------------------
# KANAL PROFİLLERİ
# -----------------------------
CHANNEL_PROFILES = {
    "Başka Bir Hayat": """
Create a cinematic photorealistic documentary-style image for a Turkish YouTube story video.

Visual identity:
- realistic contemporary Turkey
- cinematic documentary photography
- grounded and believable, never glossy advertising
- natural human proportions
- emotionally restrained, not melodramatic
- realistic Turkish architecture, streets, workplaces and interiors
- consistent visual language between scenes
- no text, captions, logos, watermarks or subtitles in the image
- horizontal YouTube composition
- 16:9
""",

    "Sessiz Düzen": """
Create a premium 2D editorial illustration for a Japanese lifestyle philosophy YouTube video.

Visual identity:
- mature Japanese woman approximately 35-40 years old when a character is required
- elegant 2D editorial illustration
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
- horizontal YouTube composition
- 16:9
"""
}


# -----------------------------
# SESSION STATE
# -----------------------------
if "sentences" not in st.session_state:
    st.session_state["sentences"] = []

if "images" not in st.session_state:
    st.session_state["images"] = {}

if "prompts" not in st.session_state:
    st.session_state["prompts"] = {}


# -----------------------------
# GÖRSEL ÜRETİM FONKSİYONU
# -----------------------------
def generate_image(scene_text, channel_name, scene_number):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı. Streamlit Secrets içindeki "
            "GEMINI_API_KEY değerini kontrol et."
        )

    profile = CHANNEL_PROFILES[channel_name]

    prompt = f"""
{profile}

SCENE NUMBER:
{scene_number:03}

NARRATION SENTENCE:
"{scene_text}"

Create a single image that visually communicates exactly this narration sentence.

Important:
- Do not write the narration sentence inside the image.
- Do not add subtitles.
- Do not add visible labels unless they naturally belong to the environment.
- The image should feel like one frame from a continuous documentary story.
- Choose the camera angle and composition that best communicates this exact moment.
"""

    interaction = client.interactions.create(
        model="gemini-3.1-flash-image",
        input=prompt,
        response_format={
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": "16:9",
            "image_size": "1K",
        },
    )

    if not interaction.output_image:
        raise RuntimeError("Gemini görsel döndürmedi.")

    image_bytes = base64.b64decode(
        interaction.output_image.data
    )

    image = Image.open(
        io.BytesIO(image_bytes)
    )

    return image, prompt


# -----------------------------
# KANAL
# -----------------------------
channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen"
    ]
)

st.divider()


# -----------------------------
# METİN
# -----------------------------
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


# -----------------------------
# SAHNELER
# -----------------------------
if st.session_state["sentences"]:

    sentences = st.session_state["sentences"]

    st.success(
        f"Metin hazır: "
        f"{len(sentences)} sahne bulundu."
    )

    st.subheader(
        "2. İlk 20 Sahne"
    )

    for index, sentence in enumerate(
        sentences[:20],
        start=1
    ):

        with st.container(border=True):

            st.markdown(
                f"### Sahne {index:03}"
            )

            st.write(sentence)

            if index in st.session_state["images"]:

                st.image(
                    st.session_state["images"][index],
                    use_container_width=True
                )

            col1, col2 = st.columns(2)

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
                                sentence,
                                channel,
                                index
                            )

                            st.session_state["images"][index] = image

                            st.session_state["prompts"][index] = prompt

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Görsel üretilemedi: {e}"
                            )

            with col2:

                if index in st.session_state["prompts"]:

                    with st.expander(
                        "✏️ Kullanılan Prompt"
                    ):

                        st.text_area(
                            "Prompt",
                            st.session_state["prompts"][index],
                            height=220,
                            key=f"prompt_view_{index}"
                        )

    if len(sentences) > 20:

        st.info(
            f"Şimdilik ilk 20 sahne gösteriliyor. "
            f"Toplam {len(sentences)} sahne var."
        )
