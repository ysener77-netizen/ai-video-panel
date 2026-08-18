import streamlit as st
import re
import io

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from PIL import Image


# =================================================
# SAYFA
# =================================================

st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Video Studio")
st.caption("Kontrollü AI video üretim paneli")


# =================================================
# GEMINI CLIENT
# =================================================

try:
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    client = None


# =================================================
# MODELLER
# =================================================

SCENE_DIRECTOR_MODEL = "gemini-3.1-flash-lite"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"


# =================================================
# SCENE DIRECTOR ŞEMASI
# =================================================

class ScenePlan(BaseModel):
    location: str = Field(
        description="Sahnenin tek ve net mekanı."
    )

    time_of_day: str = Field(
        description="Sabah, gündüz, akşam, gece gibi zaman."
    )

    main_action: str = Field(
        description="Ana karakterin görüntüde yaptığı tek ana eylem."
    )

    wardrobe: str = Field(
        description="Bu sahneye ve hikayedeki mevcut role uygun kıyafet."
    )

    accessories: str = Field(
        description="Yalnızca sahnede gerçekten gerekli aksesuarlar. Gerekmiyorsa none."
    )

    emotion: str = Field(
        description="Ana karakterin doğal duygu ve yüz ifadesi."
    )

    pose: str = Field(
        description="Karakterin beden duruşu ve hareketi."
    )

    camera: str = Field(
        description="Tek kare için uygun kamera kadrajı ve açı."
    )

    background: str = Field(
        description="Sahneyi destekleyen sade arka plan öğeleri."
    )

    continuity: str = Field(
        description="Önceki ve sonraki sahneyle görsel süreklilik için korunması gereken durum."
    )

    must_include: list[str] = Field(
        description="Görselde mutlaka olması gereken öğeler."
    )

    must_not_include: list[str] = Field(
        description="Yanlış anlamaya yol açabilecek ve kesinlikle olmaması gereken öğeler."
    )


# =================================================
# KANAL PROFİLLERİ
# =================================================

CHANNEL_PROFILES = {

    "Başka Bir Hayat": """
STYLE LOCK — BAŞKA BİR HAYAT

Create a clean, simple 2D cartoon editorial illustration.

PERMANENT CHANNEL STYLE:
- clean 2D cartoon illustration
- bold clean dark outlines
- simple rounded character anatomy
- rounded heads
- small black dot eyes
- minimal facial details
- flat matte colors
- very subtle simple shading
- muted low-saturation palette
- beige, taupe, muted brown, gray and charcoal
- clean readable environments
- simple backgrounds
- no unnecessary visual clutter
- consistent line thickness
- consistent character proportions
- horizontal 16:9 YouTube composition

MAIN CHARACTER IDENTITY LOCK:

The uploaded reference image defines ONLY WHO the recurring main
character is and the general illustration language.

PRESERVE:
- same recognizable character identity
- same head shape
- same facial proportions
- same eye style
- same ear design
- same skin tone
- same approximate age
- same body proportions
- same simple 2D cartoon construction

DO NOT COPY AS PERMANENT FEATURES:
- hat
- uniform
- shirt
- pants
- shoes
- backpack
- occupational accessories
- pose
- facial expression
- location
- profession

The reference image is NOT a wardrobe reference.
The reference image is NOT an occupation reference.

Wardrobe, accessories and expression MUST follow the current story scene.

STRICTLY AVOID:
- photography
- photorealism
- realistic skin
- 3D rendering
- Pixar style
- anime
- manga
- realistic graphic novel
- painterly illustration
- detailed realistic textures
- glossy advertising aesthetics
- dramatic photographic color grading
- text
- captions
- subtitles
- logos
- watermarks
""",

    "Sessiz Düzen": """
STYLE LOCK — SESSİZ DÜZEN

Create a premium calm 2D editorial illustration.

PERMANENT CHANNEL STYLE:
- mature Japanese woman approximately 35-40 when required
- elegant 2D editorial illustration
- warm beige
- soft ivory
- natural pale oak
- muted sage green
- low saturation
- gentle natural morning light
- minimalist Japanese environments
- calm composition
- one clear scene
- simple backgrounds
- no irrelevant objects
- no vivid colors
- no orange/yellow color cast
- horizontal 16:9
- no text
- no captions
- no logos
- no watermarks

If a reference is supplied, preserve identity but allow clothing,
expression and accessories to adapt naturally to the narration.
"""
}


# =================================================
# SESSION STATE
# =================================================

DEFAULTS = {
    "sentences": [],
    "images": {},
    "approved": {},
    "prompts": {},
    "scene_plans": {},
}

for key, default_value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# =================================================
# SCENE DIRECTOR
# =================================================

def create_scene_plan(
    current_text,
    previous_text="",
    next_text=""
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı."
        )

    director_prompt = f"""
You are the Scene Director for a narrated 2D YouTube story.

Your job is NOT to create the image.
Your job is to interpret the narration literally and produce an
unambiguous visual plan for ONE still frame.

PREVIOUS SENTENCE:
{previous_text if previous_text else "None"}

CURRENT SENTENCE:
{current_text}

NEXT SENTENCE:
{next_text if next_text else "None"}

CRITICAL RULES:

1. The CURRENT sentence is the scene that must be illustrated.
2. Previous and next sentences are context only.
3. Do not invent a new event.
4. Do not turn ordinary actions into travel, moving house, delivery,
   vacation, adventure, or another unrelated activity.
5. Never introduce luggage, suitcase, travel bag, package, uniform,
   hat, helmet, tools or work equipment unless the narration or
   immediate story context actually requires them.
6. Clothing must fit the character's CURRENT situation.
7. Do not infer the character's profession from a reference image.
8. Keep continuity with adjacent sentences.

EXAMPLES OF CORRECT INTERPRETATION:

Narration:
"Hızlıca hazırlanıp evden çıkıyorsun."

Correct interpretation:
The character has finished getting ready for a normal workday and is
leaving through the front door.

Suitable wardrobe:
ordinary workday clothes.

Possible accessory:
small everyday backpack only if useful.

Forbidden:
suitcase, rolling luggage, travel bag, airport context, moving boxes,
delivery uniform.

Narration:
"Sabah alarm çaldığında yataktan kalkıyorsun."

Correct:
bedroom, just waking up, sleepwear.

Forbidden:
work uniform, hat, backpack, suitcase.

Narration:
"Kalabalık bir otobüste işe doğru yolculuk ediyorsun."

Correct:
urban public bus, character commuting to work.

Forbidden:
tour bus, airport shuttle, vacation luggage.

Be literal, practical and visually clear.
"""

    response = client.models.generate_content(
        model=SCENE_DIRECTOR_MODEL,
        contents=director_prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ScenePlan.model_json_schema(),
        },
    )

    if not response.text:
        raise RuntimeError(
            "Scene Director sahne planı döndürmedi."
        )

    return ScenePlan.model_validate_json(
        response.text
    )


# =================================================
# GÖRSEL PROMPTU
# =================================================

def build_image_prompt(
    channel_name,
    scene_number,
    narration,
    plan
):

    style = CHANNEL_PROFILES[channel_name]

    include_text = ", ".join(
        plan.must_include
    ) if plan.must_include else "None"

    forbidden_text = ", ".join(
        plan.must_not_include
    ) if plan.must_not_include else "None"

    return f"""
{style}

SCENE {scene_number:03}

ORIGINAL NARRATION:
"{narration}"

SCENE DIRECTOR PLAN:

LOCATION:
{plan.location}

TIME:
{plan.time_of_day}

MAIN ACTION:
{plan.main_action}

WARDROBE:
{plan.wardrobe}

ACCESSORIES:
{plan.accessories}

EMOTION:
{plan.emotion}

POSE:
{plan.pose}

CAMERA:
{plan.camera}

BACKGROUND:
{plan.background}

CONTINUITY:
{plan.continuity}

MUST INCLUDE:
{include_text}

STRICTLY MUST NOT INCLUDE:
{forbidden_text}

FINAL IMAGE INSTRUCTIONS:

- Create exactly ONE still frame.
- Follow the Scene Director plan literally.
- Do not reinterpret the story.
- Do not invent another activity.
- Do not add objects because they appeared in the character reference.
- The reference image defines CHARACTER IDENTITY and DRAWING LANGUAGE only.
- Wardrobe comes from the Scene Director plan.
- Accessories come from the Scene Director plan.
- If an item appears under MUST NOT INCLUDE, it must not appear anywhere.
- Keep the recurring protagonist recognizable as the same cartoon character.
- Adapt expression and pose naturally.
- Do not write the narration in the image.
- No text.
- No subtitles.
- No logo.
- No watermark.
- Keep the frame clean and suitable for a subtle zoom or pan.
- Horizontal 16:9.
"""


# =================================================
# GÖRSEL ÜRETİM
# =================================================

def generate_scene_image(
    image_prompt,
    reference_image=None
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı."
        )

    contents = [image_prompt]

    if reference_image is not None:
        contents.append(reference_image)

    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            response_format={
                "image": {
                    "aspect_ratio": "16:9",
                    "image_size": "1K",
                }
            },
        ),
    )

    if not response.parts:
        raise RuntimeError(
            "Gemini görsel çıktısı döndürmedi."
        )

    for part in response.parts:

        if part.inline_data is not None:

            generated_image = part.as_image()

            if generated_image is not None:
                return generated_image.convert("RGB")

    raise RuntimeError(
        "Gemini yanıtında kullanılabilir görsel bulunamadı."
    )


# =================================================
# KANAL SEÇİMİ
# =================================================

channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen",
    ]
)


# =================================================
# REFERANS KARAKTER
# =================================================

st.subheader("🎭 Karakter Referansı")

uploaded_reference = st.file_uploader(
    "Ana karakter referans görselini yükle",
    type=["png", "jpg", "jpeg"],
)

reference_image = None

if uploaded_reference is not None:

    reference_image = Image.open(
        uploaded_reference
    ).convert("RGB")

    col_ref1, col_ref2 = st.columns(
        [1, 3]
    )

    with col_ref1:

        st.image(
            reference_image,
            caption="Referans karakter",
            use_container_width=True,
        )

    with col_ref2:

        st.success(
            "Referans yüklendi. Karakter kimliği korunacak; "
            "kıyafet, aksesuar ve ifade sahneye göre belirlenecek."
        )

elif channel == "Başka Bir Hayat":

    st.warning(
        "Başka Bir Hayat için referans karakter yüklemeden "
        "seri üretime geçme."
    )


st.divider()


# =================================================
# VIDEO METNİ
# =================================================

st.subheader("1. Video Metni")

script = st.text_area(
    "Video metnini buraya yapıştır",
    height=300,
)


if st.button(
    "Metni Cümlelere Ayır",
    type="primary",
):

    if not script.strip():

        st.warning(
            "Önce video metnini gir."
        )

    else:

        sentences = re.split(
            r'(?<=[.!?])\s+',
            script.strip(),
        )

        sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

        st.session_state.sentences = sentences
        st.session_state.images = {}
        st.session_state.approved = {}
        st.session_state.prompts = {}
        st.session_state.scene_plans = {}


# =================================================
# SAHNELER
# =================================================

if st.session_state.sentences:

    sentences = st.session_state.sentences

    approved_count = sum(
        1
        for approved
        in st.session_state.approved.values()
        if approved
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

    st.subheader(
        "2. İlk 20 Sahne"
    )


    for index, sentence in enumerate(
        sentences[:20],
        start=1,
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

        approved = (
            st.session_state.approved.get(
                index,
                False,
            )
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {'✅' if approved else '⏳'} "
                f"Sahne {index:03}"
            )

            st.write(
                sentence
            )

            # --------------------------------------
            # SAHNE PLANI
            # --------------------------------------

            if index in st.session_state.scene_plans:

                plan = (
                    st.session_state.scene_plans[index]
                )

                with st.expander(
                    "🎬 Scene Director Planı"
                ):

                    st.write(
                        f"**Mekân:** {plan.location}"
                    )

                    st.write(
                        f"**Zaman:** {plan.time_of_day}"
                    )

                    st.write(
                        f"**Eylem:** {plan.main_action}"
                    )

                    st.write(
                        f"**Kıyafet:** {plan.wardrobe}"
                    )

                    st.write(
                        f"**Aksesuar:** {plan.accessories}"
                    )

                    st.write(
                        f"**Duygu:** {plan.emotion}"
                    )

                    st.write(
                        f"**Kamera:** {plan.camera}"
                    )

                    st.write(
                        "**Olmaması gerekenler:** "
                        + ", ".join(
                            plan.must_not_include
                        )
                    )


            # --------------------------------------
            # GÖRSEL
            # --------------------------------------

            if index in st.session_state.images:

                st.image(
                    st.session_state.images[index],
                    use_container_width=True,
                )


            # --------------------------------------
            # BUTONLAR
            # --------------------------------------

            col1, col2 = st.columns(2)


            with col1:

                button_label = (
                    "🔄 Yeniden Üret"
                    if index in st.session_state.images
                    else "🎨 Görsel Üret"
                )

                if st.button(
                    button_label,
                    key=f"generate_{index}",
                    use_container_width=True,
                ):

                    with st.spinner(
                        f"Sahne {index:03} yorumlanıyor ve hazırlanıyor..."
                    ):

                        try:

                            # Yeniden üretmede önceki planı kullan.
                            # Böylece doğru anlam korunurken sadece görsel değişir.

                            if index in st.session_state.scene_plans:

                                plan = (
                                    st.session_state.scene_plans[index]
                                )

                            else:

                                plan = create_scene_plan(
                                    current_text=sentence,
                                    previous_text=previous_text,
                                    next_text=next_text,
                                )

                                st.session_state.scene_plans[index] = plan


                            image_prompt = build_image_prompt(
                                channel_name=channel,
                                scene_number=index,
                                narration=sentence,
                                plan=plan,
                            )


                            generated_image = generate_scene_image(
                                image_prompt=image_prompt,
                                reference_image=reference_image,
                            )


                            st.session_state.images[index] = generated_image

                            st.session_state.prompts[index] = image_prompt

                            st.session_state.approved[index] = False


                            st.rerun()


                        except Exception as e:

                            st.error(
                                f"Sahne üretilemedi: {e}"
                            )


            with col2:

                if index in st.session_state.images:

                    if st.button(
                        "✅ Onayla",
                        key=f"approve_{index}",
                        use_container_width=True,
                        disabled=approved,
                    ):

                        st.session_state.approved[index] = True

                        st.rerun()


            # --------------------------------------
            # PROMPT
            # --------------------------------------

            if index in st.session_state.prompts:

                with st.expander(
                    "✏️ Görsel Promptu"
                ):

                    st.text_area(
                        "Prompt",
                        st.session_state.prompts[index],
                        height=300,
                        key=f"prompt_{index}",
                    )


    if len(sentences) > 20:

        st.info(
            f"İlk 20 sahne gösteriliyor. "
            f"Toplam {len(sentences)} sahne var."
        )
