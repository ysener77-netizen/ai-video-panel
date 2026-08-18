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

STRICT CHANNEL STYLE:
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
- clear visual storytelling
- horizontal 16:9 YouTube frame

MAIN CHARACTER IDENTITY:
The uploaded reference image defines ONLY the permanent identity and drawing design of the recurring main male character.

PRESERVE FROM THE REFERENCE:
- same recognizable face
- same head shape
- same facial proportions
- same eye design
- same ear design
- same skin tone
- same approximate age
- same body proportions
- same overall 2D cartoon design
- same recognizable identity across every scene

DO NOT PERMANENTLY COPY FROM THE REFERENCE:
- clothes
- uniform
- shirt
- pants
- jacket
- shoes
- hat or cap
- backpack
- work accessories
- occupational appearance
- pose
- facial expression
- background

The reference tells you WHO the character is.
It does NOT tell you what job he has or what he must wear.

WARDROBE AND ACCESSORIES:
Choose clothing and accessories naturally from the CURRENT SCENE and STORY CONTEXT.

Examples:
- sleeping or waking up: simple pajamas or sleepwear, no hat
- at home: casual home clothing
- commuting to an office: normal everyday or office-appropriate clothing
- office employee: shirt, polo, sweater or other believable office clothing, no delivery uniform
- job interview: neat interview clothing
- delivery worker: delivery work clothes only when the story says he is a delivery worker
- construction worker: appropriate construction clothes only when required
- unemployed at home: simple casual clothes
- cold outdoor scene: jacket or coat when appropriate

Never infer the character's profession from the reference image.

CHARACTER EXPRESSION:
The face identity must remain the same, but expressions should change naturally:
- tired
- worried
- sad
- surprised
- relieved
- happy
- determined
according to the narration.

VISUAL CONTINUITY:
Every frame must look like it belongs to the same animated illustrated series.
Maintain the same line weight, palette, proportions and illustration style.

STRICTLY AVOID:
- photography
- photorealism
- realistic skin texture
- 3D rendering
- Pixar style
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

If a reference image is supplied, preserve the same woman's identity while allowing clothing and accessories to change naturally with the scene.
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
# SAHNE BAĞLAMI YARDIMCISI
# -------------------------------------------------

def build_scene_context(scene_text, previous_text="", next_text=""):

    return f"""
CURRENT NARRATION:
{scene_text}

PREVIOUS NARRATION:
{previous_text if previous_text else "None"}

NEXT NARRATION:
{next_text if next_text else "None"}

Interpret the character's clothing, accessories, environment and emotional state from these story details.

Do not copy clothing or occupational cues from the reference image unless they are actually appropriate for this scene.
"""


# -------------------------------------------------
# GÖRSEL ÜRETİM
# -------------------------------------------------

def generate_scene(
    scene_text,
    channel_name,
    scene_number,
    reference_image=None,
    previous_text="",
    next_text=""
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı. GEMINI_API_KEY değerini kontrol et."
        )

    profile = CHANNEL_PROFILES[channel_name]

    scene_context = build_scene_context(
        scene_text=scene_text,
        previous_text=previous_text,
        next_text=next_text
    )

    prompt = f"""
{profile}

SCENE NUMBER: {scene_number:03}

{scene_context}

CREATE EXACTLY ONE IMAGE.

SCENE RULES:
- illustrate the exact current narration moment
- use previous and next narration only to understand continuity
- do not combine multiple moments into one frame
- wardrobe must fit the current scene
- accessories must fit the current scene
- do not preserve the reference image's uniform or hat unless appropriate
- keep the recurring character's face and core identity unchanged
- maintain the channel's exact 2D cartoon style
- no text inside the image
- no subtitles
- no logos
- no watermark
- composition suitable for gentle zoom or pan
- horizontal 16:9

REFERENCE IMAGE RULE:
The supplied image is an IDENTITY + ART STYLE reference only.
It is NOT a wardrobe reference.
It is NOT an occupation reference.
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

    if not response.candidates:
        raise RuntimeError("Gemini hiçbir aday sonuç döndürmedi.")

    image_found = None

    for part in response.candidates[0].content.parts:

        if part.inline_data is not None:

            mime_type = part.inline_data.mime_type or ""

            if mime_type.startswith("image/"):

                image_found = Image.open(
                    io.BytesIO(part.inline_data.data)
                ).convert("RGB")

                break

    if image_found is None:
        raise RuntimeError("Gemini görsel çıktısı döndürmedi.")

    return image_found, prompt


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
            "Referans yüklendi. Kimlik ve çizim stili korunacak; "
            "kıyafet ve aksesuarlar sahneye göre değişecek."
        )

else:

    if channel == "Başka Bir Hayat":
        st.warning(
            "Başka Bir Hayat için referans karakter yüklemeden seri üretime geçme."
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

        st.warning("Önce video metnini gir.")

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
        for value in st.session_state.approved.values()
        if value
    )

    st.success(
        f"{len(sentences)} sahne bulundu."
    )

    st.progress(
        approved_count / len(sentences)
    )

    st.caption(
        f"Onaylanan: {approved_count}/{len(sentences)}"
    )

    st.subheader("2. İlk 20 Sahne")

    for index, sentence in enumerate(
        sentences[:20],
        start=1
    ):

        previous_text = (
            sentences[index - 2]
            if index > 1
            else ""
        )

        next_text = (
            sentences[index]
            if index < len(sentences)
            else ""
        )

        with st.container(border=True):

            approved = st.session_state.approved.get(
                index,
                False
            )

            st.markdown(
                f"### {'✅' if approved else '⏳'} Sahne {index:03}"
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
                                reference_image=reference_image,
                                previous_text=previous_text,
                                next_text=next_text
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

                with st.expander("✏️ Kullanılan Prompt"):

                    st.text_area(
                        "Prompt",
                        st.session_state.prompts[index],
                        height=260,
                        key=f"prompt_{index}"
                    )

    if len(sentences) > 20:

        st.info(
            f"İlk 20 sahne gösteriliyor. Toplam {len(sentences)} sahne var."
        )
