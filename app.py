import streamlit as st
import re
import io

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from PIL import Image


# =========================================================
# SAYFA
# =========================================================

st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Video Studio")
st.caption("Kontrollü AI video üretim paneli")


# =========================================================
# GEMINI
# =========================================================

try:
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    client = None


SCENE_DIRECTOR_MODEL = "gemini-3.1-flash-lite"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"


# =========================================================
# SCENE DIRECTOR ŞEMASI
# =========================================================

class ScenePlan(BaseModel):

    location: str = Field(
        description="Tek ve net sahne mekanı."
    )

    time_of_day: str = Field(
        description="Sabah, gündüz, akşam veya gece."
    )

    main_action: str = Field(
        description="Karakterin karede yaptığı tek ana eylem."
    )

    wardrobe_change_required: bool = Field(
        description=(
            "Önceki sahnedeki kıyafetin gerçekten değiştirilmesi "
            "gerekiyorsa true. Aksi halde false."
        )
    )

    wardrobe_change_reason: str = Field(
        description=(
            "Kıyafet neden değişmeli veya neden aynı kalmalı."
        )
    )

    proposed_new_outfit: str = Field(
        description=(
            "Yalnızca wardrobe_change_required true ise yeni kıyafetin "
            "çok kesin tanımı. Renk, üst, alt, ayakkabı dahil. "
            "Değişiklik gerekmiyorsa SAME."
        )
    )

    accessories: str = Field(
        description=(
            "Sadece gerçekten gerekli aksesuarlar. Gerekmiyorsa none."
        )
    )

    emotion: str = Field(
        description="Doğal duygu ve yüz ifadesi."
    )

    pose: str = Field(
        description="Beden duruşu."
    )

    camera: str = Field(
        description="Kamera kadrajı ve açı."
    )

    background: str = Field(
        description="Sade ve sahneye uygun arka plan."
    )

    continuity: str = Field(
        description="Önceki sahneyle korunması gereken durum."
    )

    must_include: list[str] = Field(
        description="Mutlaka görünmesi gereken öğeler."
    )

    must_not_include: list[str] = Field(
        description="Kesinlikle görünmemesi gereken öğeler."
    )


# =========================================================
# KANAL PROFİLLERİ
# =========================================================

CHANNEL_PROFILES = {

    "Başka Bir Hayat": """
STYLE LOCK — BAŞKA BİR HAYAT

Create a clean simple 2D cartoon editorial illustration.

PERMANENT VISUAL STYLE:

- clean 2D cartoon illustration
- bold clean dark outlines
- rounded simplified human anatomy
- rounded head construction
- simple black dot eyes
- minimal facial details
- flat matte colors
- subtle simple shading only
- low saturation
- beige
- muted brown
- taupe
- gray
- charcoal
- clean environments
- uncluttered composition
- consistent line thickness
- consistent character proportions
- horizontal 16:9


CHARACTER IDENTITY LOCK:

The uploaded reference image defines the recurring protagonist's
PERMANENT PHYSICAL AND DRAWING IDENTITY.

ALWAYS PRESERVE:

- recognizable face
- head shape
- facial proportions
- eye style
- ear design
- skin tone
- approximate age
- body proportions
- overall simplified 2D cartoon construction


REFERENCE IMAGE DOES NOT DEFINE:

- current clothing
- profession
- hat
- uniform
- backpack
- accessories
- pose
- emotion
- location


WARDROBE CONTINUITY IS CRITICAL:

When an ACTIVE OUTFIT LOCK is supplied in the prompt,
reproduce that outfit exactly.

Preserve:
- exact garment type
- exact garment colors
- exact pants color
- exact shoe color
- jacket / hoodie / shirt status
- visible layers

Do NOT redesign the outfit.
Do NOT substitute colors.
Do NOT randomly change clothing between consecutive scenes.

Only use a different outfit when the prompt explicitly provides
a NEW ACTIVE OUTFIT LOCK.


STRICTLY AVOID:

- photography
- photorealism
- realistic skin texture
- 3D rendering
- Pixar
- anime
- manga
- realistic graphic novel
- painterly rendering
- glossy advertising look
- vivid saturated colors
- text
- subtitles
- captions
- logos
- watermarks
""",

    "Sessiz Düzen": """
STYLE LOCK — SESSİZ DÜZEN

Create a premium calm 2D Japanese editorial illustration.

- mature Japanese woman approximately 35-40 when required
- warm beige
- soft ivory
- pale natural oak
- muted sage green
- low saturation
- elegant 2D editorial illustration
- gentle natural light
- minimalist Japanese interiors
- simple composition
- horizontal 16:9
- no vivid colors
- no orange cast
- no text
- no captions
- no logos
- no watermarks

Preserve reference identity consistently.
"""
}


# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {
    "sentences": [],
    "images": {},
    "approved": {},
    "prompts": {},
    "scene_plans": {},
    "outfit_by_scene": {},
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# YARDIMCI
# =========================================================

def get_previous_outfit(scene_number):

    if scene_number <= 1:
        return ""

    previous_scene = scene_number - 1

    return st.session_state.outfit_by_scene.get(
        previous_scene,
        ""
    )


# =========================================================
# SCENE DIRECTOR
# =========================================================

def create_scene_plan(
    current_text,
    previous_text="",
    next_text="",
    previous_outfit=""
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı."
        )

    current_outfit_text = (
        previous_outfit
        if previous_outfit
        else "NO PREVIOUS OUTFIT — establish an appropriate first outfit."
    )

    director_prompt = f"""
You are the Scene Director for a consistent illustrated YouTube story.

Your task is to understand ONE narration sentence and create
a precise visual plan.

PREVIOUS NARRATION:
{previous_text if previous_text else "None"}

CURRENT NARRATION:
{current_text}

NEXT NARRATION:
{next_text if next_text else "None"}


CURRENT LOCKED OUTFIT:
{current_outfit_text}


WARDROBE CONTINUITY IS EXTREMELY IMPORTANT.

DEFAULT RULE:
KEEP THE CURRENT LOCKED OUTFIT EXACTLY THE SAME.

Do NOT change:
- shirt color
- hoodie color
- jacket color
- pants color
- shoes
- visible clothing layers

simply because the character enters another location.


ONLY change outfit if the story context clearly requires a genuine
wardrobe transition.


VALID OUTFIT CHANGE EXAMPLES:

- waking up in sleepwear then getting dressed for work
- explicitly changing clothes
- showering and dressing
- starting a job requiring a uniform
- preparing for a formal interview
- changing into pajamas before sleeping
- changing into sports clothes for exercise


NOT VALID REASONS TO CHANGE OUTFIT:

- entering a bus
- entering an office
- sitting at a desk
- talking to the boss
- walking outside
- eating lunch
- going home
- changing camera angle
- changing emotion


If wardrobe_change_required is FALSE:

proposed_new_outfit MUST be exactly:
SAME


If wardrobe_change_required is TRUE:

create ONE precise canonical outfit description.

Example:

dark charcoal zip hoodie,
muted beige crew-neck T-shirt,
dark gray straight trousers,
dark brown casual shoes,
no hat

This description will become permanently locked for following scenes,
so choose sensible specific colors and garments.


SEMANTIC RULES:

1. Illustrate the CURRENT sentence literally.

2. Previous and next sentences are context only.

3. Do not invent unrelated events.

4. Do not interpret leaving home as travel or vacation.

5. Do not add luggage unless explicitly necessary.

6. Never infer occupation from the character reference image.

7. Accessories should be minimal and logically required.


EXAMPLE:

Previous:
"Sabah alarm çaldığında yataktan kalkıyorsun."

Current locked outfit:
muted taupe striped pajamas

Current:
"Hızlıca hazırlanıp evden çıkıyorsun."

This IS a legitimate wardrobe change because the person changes
from sleepwear into workday clothing.

Choose ONE precise workday outfit and lock it.


Next:
"Kalabalık bir otobüste işe doğru yolculuk ediyorsun."

The outfit MUST NOT change again.
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
            "Scene Director sonuç döndürmedi."
        )

    plan = ScenePlan.model_validate_json(
        response.text
    )

    return plan


# =========================================================
# OUTFIT LOCK KARARI
# =========================================================

def resolve_outfit(
    scene_number,
    plan
):

    previous_outfit = get_previous_outfit(
        scene_number
    )

    # İlk sahne
    if not previous_outfit:

        if (
            plan.proposed_new_outfit
            and plan.proposed_new_outfit.upper() != "SAME"
        ):
            active_outfit = plan.proposed_new_outfit

        else:
            active_outfit = (
                "simple muted taupe casual clothing, "
                "dark gray trousers, brown casual shoes, no hat"
            )

    # Gerçek kıyafet değişimi
    elif (
        plan.wardrobe_change_required
        and plan.proposed_new_outfit.upper() != "SAME"
    ):

        active_outfit = plan.proposed_new_outfit

    # Aynı kıyafet KELİMESİ KELİMESİNE devam
    else:

        active_outfit = previous_outfit


    st.session_state.outfit_by_scene[
        scene_number
    ] = active_outfit

    return active_outfit


# =========================================================
# GÖRSEL PROMPT
# =========================================================

def build_image_prompt(
    channel_name,
    scene_number,
    narration,
    plan,
    active_outfit
):

    style = CHANNEL_PROFILES[
        channel_name
    ]

    include_text = (
        ", ".join(plan.must_include)
        if plan.must_include
        else "None"
    )

    forbidden_text = (
        ", ".join(plan.must_not_include)
        if plan.must_not_include
        else "None"
    )

    prompt = f"""
{style}


SCENE:
{scene_number:03}


NARRATION:
"{narration}"


SCENE PLAN:


LOCATION:
{plan.location}


TIME:
{plan.time_of_day}


ACTION:
{plan.main_action}


EMOTION:
{plan.emotion}


POSE:
{plan.pose}


CAMERA:
{plan.camera}


BACKGROUND:
{plan.background}


ACCESSORIES:
{plan.accessories}


CONTINUITY:
{plan.continuity}


========================================

ACTIVE OUTFIT LOCK

{active_outfit}

========================================


OUTFIT LOCK IS MANDATORY.

The protagonist must wear EXACTLY this outfit.

Do not:
- change garment colors
- replace a hoodie with a jacket
- replace a shirt with another shirt
- change pants color
- change shoe color
- add a hat
- remove a visible layer

unless the ACTIVE OUTFIT LOCK explicitly says so.


REFERENCE IMAGE:

The reference image defines CHARACTER IDENTITY.

The ACTIVE OUTFIT LOCK defines CLOTHING.

Do not confuse these two.


MUST INCLUDE:
{include_text}


MUST NOT INCLUDE:
{forbidden_text}


FINAL RULES:

- exactly one still scene
- exact narration moment
- no unrelated events
- no invented props
- same recurring protagonist
- same character construction
- exact ACTIVE OUTFIT LOCK
- simple 2D cartoon style
- suitable for subtle zoom/pan
- horizontal 16:9
- no text
- no subtitles
- no logos
- no watermarks
"""

    return prompt


# =========================================================
# REFERANS GÖRSEL PART
# =========================================================

def image_to_part(image):

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=95
    )

    return types.Part.from_bytes(
        data=buffer.getvalue(),
        mime_type="image/jpeg"
    )


# =========================================================
# GÖRSEL ÜRETİM
# =========================================================

def generate_scene_image(
    image_prompt,
    reference_image=None
):

    if client is None:
        raise RuntimeError(
            "Gemini API bağlantısı kurulamadı."
        )

    contents = [
        image_prompt
    ]

    if reference_image is not None:

        contents.append(
            image_to_part(
                reference_image
            )
        )


    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=[
                "IMAGE"
            ],
            image_config=types.ImageConfig(
                aspect_ratio="16:9"
            )
        )
    )


    if not response.candidates:
        raise RuntimeError(
            "Gemini görsel döndürmedi."
        )


    for candidate in response.candidates:

        if candidate.content is None:
            continue

        for part in (
            candidate.content.parts
            or []
        ):

            if part.inline_data is None:
                continue

            mime_type = (
                part.inline_data.mime_type
                or ""
            )

            if mime_type.startswith(
                "image/"
            ):

                return Image.open(
                    io.BytesIO(
                        part.inline_data.data
                    )
                ).convert("RGB")


    raise RuntimeError(
        "Görsel bulunamadı."
    )


# =========================================================
# KANAL
# =========================================================

channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen"
    ]
)


# =========================================================
# REFERANS
# =========================================================

st.subheader(
    "🎭 Karakter Referansı"
)

uploaded_reference = st.file_uploader(
    "Ana karakter referans görselini yükle",
    type=[
        "png",
        "jpg",
        "jpeg"
    ]
)

reference_image = None


if uploaded_reference is not None:

    reference_image = Image.open(
        uploaded_reference
    ).convert("RGB")


    col_a, col_b = st.columns(
        [
            1,
            3
        ]
    )


    with col_a:

        st.image(
            reference_image,
            caption="Referans karakter",
            use_container_width=True
        )


    with col_b:

        st.success(
            "Karakter kimliği referanstan korunacak. "
            "Kıyafet ise hikâyedeki wardrobe lock sistemiyle yönetilecek."
        )


elif channel == "Başka Bir Hayat":

    st.warning(
        "Referans karakter yüklemeden seri üretime geçme."
    )


st.divider()


# =========================================================
# METİN
# =========================================================

st.subheader(
    "1. Video Metni"
)

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
        st.session_state.scene_plans = {}
        st.session_state.outfit_by_scene = {}


# =========================================================
# SAHNELER
# =========================================================

if st.session_state.sentences:

    sentences = (
        st.session_state.sentences
    )


    approved_count = sum(
        1
        for value in
        st.session_state.approved.values()
        if value
    )


    st.success(
        f"{len(sentences)} sahne bulundu."
    )


    st.progress(
        approved_count
        / len(sentences)
    )


    st.caption(
        f"Onaylanan: "
        f"{approved_count}/{len(sentences)}"
    )


    st.subheader(
        "2. İlk 20 Sahne"
    )


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


        approved = (
            st.session_state.approved.get(
                index,
                False
            )
        )


        with st.container(
            border=True
        ):


            st.markdown(
                f"### "
                f"{'✅' if approved else '⏳'} "
                f"Sahne {index:03}"
            )


            st.write(
                sentence
            )


            # ---------------------------------
            # OUTFIT GÖSTER
            # ---------------------------------

            if index in st.session_state.outfit_by_scene:

                st.info(
                    "👕 Aktif Kıyafet Kilidi: "
                    + st.session_state.outfit_by_scene[
                        index
                    ]
                )


            # ---------------------------------
            # SCENE PLAN
            # ---------------------------------

            if index in st.session_state.scene_plans:

                plan = (
                    st.session_state.scene_plans[
                        index
                    ]
                )


                with st.expander(
                    "🎬 Scene Director Planı"
                ):


                    st.write(
                        f"**Mekân:** "
                        f"{plan.location}"
                    )


                    st.write(
                        f"**Eylem:** "
                        f"{plan.main_action}"
                    )


                    st.write(
                        f"**Kıyafet değişmeli mi:** "
                        f"{plan.wardrobe_change_required}"
                    )


                    st.write(
                        f"**Sebep:** "
                        f"{plan.wardrobe_change_reason}"
                    )


                    st.write(
                        f"**Yeni kıyafet önerisi:** "
                        f"{plan.proposed_new_outfit}"
                    )


                    st.write(
                        f"**Duygu:** "
                        f"{plan.emotion}"
                    )


            # ---------------------------------
            # GÖRSEL
            # ---------------------------------

            if index in st.session_state.images:

                st.image(
                    st.session_state.images[
                        index
                    ],
                    use_container_width=True
                )


            # ---------------------------------
            # BUTONLAR
            # ---------------------------------

            col1, col2 = st.columns(
                2
            )


            with col1:


                label = (
                    "🔄 Aynı Planla Yeniden Üret"
                    if index in
                    st.session_state.images
                    else
                    "🎨 Görsel Üret"
                )


                if st.button(
                    label,
                    key=f"generate_{index}",
                    use_container_width=True
                ):


                    # Sahne sırasını zorunlu tutuyoruz.
                    # Böylece kıyafet zinciri bozulmaz.

                    if (
                        index > 1
                        and (index - 1)
                        not in
                        st.session_state.outfit_by_scene
                    ):

                        st.error(
                            "Tutarlılık için önce bir önceki sahneyi üret."
                        )

                    else:


                        with st.spinner(
                            f"Sahne {index:03} hazırlanıyor..."
                        ):


                            try:


                                # --------------------------
                                # PLAN
                                # --------------------------

                                if index in st.session_state.scene_plans:

                                    plan = (
                                        st.session_state.scene_plans[
                                            index
                                        ]
                                    )

                                else:

                                    previous_outfit = (
                                        get_previous_outfit(
                                            index
                                        )
                                    )


                                    plan = create_scene_plan(
                                        current_text=sentence,
                                        previous_text=previous_text,
                                        next_text=next_text,
                                        previous_outfit=previous_outfit
                                    )


                                    st.session_state.scene_plans[
                                        index
                                    ] = plan


                                # --------------------------
                                # OUTFIT LOCK
                                # --------------------------

                                active_outfit = (
                                    resolve_outfit(
                                        scene_number=index,
                                        plan=plan
                                    )
                                )


                                # --------------------------
                                # PROMPT
                                # --------------------------

                                image_prompt = (
                                    build_image_prompt(
                                        channel_name=channel,
                                        scene_number=index,
                                        narration=sentence,
                                        plan=plan,
                                        active_outfit=active_outfit
                                    )
                                )


                                # --------------------------
                                # IMAGE
                                # --------------------------

                                generated_image = (
                                    generate_scene_image(
                                        image_prompt=image_prompt,
                                        reference_image=reference_image
                                    )
                                )


                                st.session_state.images[
                                    index
                                ] = generated_image


                                st.session_state.prompts[
                                    index
                                ] = image_prompt


                                st.session_state.approved[
                                    index
                                ] = False


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
                        disabled=approved
                    ):


                        st.session_state.approved[
                            index
                        ] = True


                        st.rerun()


            # ---------------------------------
            # PROMPT
            # ---------------------------------

            if index in st.session_state.prompts:


                with st.expander(
                    "✏️ Görsel Promptu"
                ):


                    st.text_area(
                        "Prompt",
                        st.session_state.prompts[
                            index
                        ],
                        height=320,
                        key=f"prompt_{index}"
                    )


    if len(sentences) > 20:

        st.info(
            f"İlk 20 sahne gösteriliyor. "
            f"Toplam {len(sentences)} sahne var."
        )
