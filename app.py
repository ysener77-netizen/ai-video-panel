import streamlit as st
import re
import io

from google import genai
from google.genai import types
from PIL import Image


# -------------------------------------------------
# SAYFA
# -------------------------------------------------

st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Video Studio")
st.caption("Kontrollü AI video üretim paneli")


# -------------------------------------------------
# GEMINI CLIENT
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
Create a clean 2D cartoon editorial illustration for a Turkish YouTube life-story video.

STRICT CHANNEL VISUAL STYLE:
- simple clean 2D cartoon illustration
- bold clean dark outlines
- rounded simplified human proportions
- rounded heads
- small black dot eyes
- minimal nose and mouth
- flat matte colors
- subtle simple shading only
- low saturation
- beige, muted brown, taupe, gray and charcoal palette
- simple clean environments
- uncluttered composition
- clear storytelling
- horizontal 16:9 YouTube frame

MAIN CHARACTER:
If a reference image is supplied, the person in that image defines the
recurring main male character.

Preserve:
- same face shape
- same eyes
- same ears
- same head proportions
- same recognizable cartoon identity
- same general body proportions

Clothing and accessories may change only when logically required by the story.

The result must look like another frame from the same simple illustrated cartoon series.

STRICTLY AVOID:
- photography
- photorealism
- realistic skin
- realistic human anatomy
- 3D rendering
- Pixar
- anime
- manga
- realistic graphic novel art
- painterly art
- hyper-detailed textures
- dramatic photographic lighting
- glossy advertising look
- text
- subtitles
- captions
- logos
- watermarks
""",

    "Sessiz Düzen": """
Create a premium calm 2D editorial illustration for a Japanese lifestyle YouTube video.

VISUAL STYLE:
- mature Japanese woman approximately 35-40 when required
- elegant 2D editorial illustration
- warm beige
- soft ivory
- natural pale oak
- muted sage green
- low saturation
- gentle natural morning light
- minimalist Japanese interiors
- simple cinematic composition
- one clear scene only
- no irrelevant objects
- no vivid colors
- no orange/yellow cast
- no text
- no captions
- no logos
- no watermarks
- horizontal 16:9

If a reference image is supplied, preserve the same woman's identity.
"""
}


# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------

if "sentences" not in st.session_state:
    st.session_state.sentences = []

if "images" not in st.session_state:
    st.session_state.images = {}

if "approved" not in st.session_state:
    st.session_state.approved = {}

if "prompts" not in st.session_state:
    st.session_state.prompts = {}


# -------------------------------------------------
# GÖRSEL ÜRETİM
# -------------------------------------------------

def generate_scene(
    scene_text,
    channel_name,
    scene_number,
    reference_image=None
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı. "
            "GEMINI_API_KEY değerini kontrol et."
        )

    profile = CHANNEL_PROFILES[channel_name]

    prompt = f"""
{profile}

SCENE NUMBER: {scene_number:03}

NARRATION:
{scene_text}

Create exactly ONE scene for this narration.

Important:
- visually communicate this exact moment
- do not write narration in the image
- do not invent unrelated actions
- maintain the same channel art style
- keep composition suitable for gentle zoom/pan
- horizontal 16:9

If a character reference image is included:
Use it as the identity and style reference for the recurring main character.
Do not replace the character with another person.
"""

    contents = [prompt]

    if reference_image is not None:

        buffer = io.BytesIO()
        reference_image.save(
            buffer,
            format="JPEG",
            quality=95
        )

        contents.append(
            types.Part.from_bytes(
                data=buffer.getvalue(),
                mime_type="image/jpeg"
            )
        )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="16:9"
            )
        )
    )

    image_found = None

    if not response.candidates:
        raise RuntimeError(
            "Gemini hiçbir aday sonuç döndürmedi."
        )

    for part in response.candidates[0].content.parts:

        if part.inline_data is not None:

            mime_type = (
                part.inline_data.mime_type
                or ""
            )

            if mime_type.startswith("image/"):

                image_found = Image.open(
                    io.BytesIO(
                        part.inline_data.data
                    )
                ).convert("RGB")

                break

    if image_found is None:
        raise RuntimeError(
            "Gemini görsel çıktısı döndürmedi."
        )

    return image_found, prompt


# -------------------------------------------------
# KANAL SEÇİMİ
# -------------------------------------------------

channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen"
    ]
)


# -------------------------------------------------
# KARAKTER REFERANSI
# -------------------------------------------------

st.subheader("🎭 Karakter Referansı")

uploaded_reference = st.file_uploader(
    "Ana karakter referans görselini yükle",
    type=["png", "jpg", "jpeg"]
)

reference_image = None

if uploaded_reference is not None:

    reference_image = Image.open(
        uploaded_reference
    ).convert("RGB")

    col_a, col_b = st.columns([1, 3])

    with col_a:

        st.image(
            reference_image,
            caption="Referans karakter",
            use_container_width=True
        )

    with col_b:

        st.success(
            "Referans yüklendi. "
            "Sahnelerde karakter kimliğini korumak için kullanılacak."
        )

else:

    if channel == "Başka Bir Hayat":

        st.warning(
            "Başka Bir Hayat için referans karakter yüklemeden "
            "seri üretime geçme."
        )


st.divider()


# -------------------------------------------------
# VIDEO METNİ
# -------------------------------------------------

st.subheader("1. Video Metni")

script = st.text_area(
    "Video metnini buraya yapıştır",
    height=300
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
            s.strip()
            for s in sentences
            if s.strip()
        ]

        st.session_state.sentences = sentences
        st.session_state.images = {}
        st.session_state.approved = {}
        st.session_state.prompts = {}


# -------------------------------------------------
# SAHNELER
# -------------------------------------------------

if st.session_state.sentences:

    sentences = st.session_state.sentences

    approved_count = sum(
        1
        for value
        in st.session_state.approved.values()
        if value
    )

    st.success(
        f"{len(sentences)} sahne bulundu."
    )

    st.progress(
        approved_count / len(sentences)
    )

    st.caption(
        f"Onaylanan: "
        f"{approved_count}/{len(sentences)}"
    )

    st.subheader("2. İlk 20 Sahne")

    for index, sentence in enumerate(
        sentences[:20],
        start=1
    ):

        with st.container(border=True):

            approved = st.session_state.approved.get(
                index,
                False
            )

            st.markdown(
                f"### {'✅' if approved else '⏳'} "
                f"Sahne {index:03}"
            )

            st.write(sentence)

            if index in st.session_state.images:

                st.image(
                    st.session_state.images[index],
                    use_container_width=True
                )

            col1, col2 = st.columns(2)

            with col1:

                label = (
                    "🔄 Yeniden Üret"
                    if index in st.session_state.images
                    else "🎨 Görsel Üret"
                )

                if st.button(
                    label,
                    key=f"generate_{index}",
                    use_container_width=True
                ):

                    with st.spinner(
                        f"Sahne {index:03} hazırlanıyor..."
                    ):

                        try:

                            image, prompt = generate_scene(
                                scene_text=sentence,
                                channel_name=channel,
                                scene_number=index,
                                reference_image=reference_image
                            )

                            st.session_state.images[index] = image
                            st.session_state.prompts[index] = prompt
                            st.session_state.approved[index] = False

                            st.rerun()

                        except Exception as e:

                            st.error(
                                f"Görsel üretilemedi: {e}"
                            )

            with col2:

                if index in st.session_state.images:

                    if st.button(
                        "✅ Onayla",
                        key=f"approve_{index}",
                        use_container_width=True,
                        disabled=approved
                    ):

                        st.session_state.approved[index] = True
                        st.rerun()

            if index in st.session_state.prompts:

                with st.expander(
                    "✏️ Kullanılan Prompt"
                ):

                    st.text_area(
                        "Prompt",
                        st.session_state.prompts[index],
                        height=240,
                        key=f"prompt_{index}"
                    )

    if len(sentences) > 20:

        st.info(
            f"İlk 20 sahne gösteriliyor. "
            f"Toplam {len(sentences)} sahne var."
        )
