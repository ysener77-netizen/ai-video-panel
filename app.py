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

    natural_behavior: str = Field(
        description=(
            "Bu anda gerçek bir insanın doğal olarak nasıl görüneceği "
            "ve ne yapacağı."
        )
    )

    wardrobe_change_required: bool = Field(
        description=(
            "Önceki kıyafetin gerçekten değiştirilmesi gerekiyorsa true."
        )
    )

    wardrobe_change_reason: str = Field(
        description="Kıyafet neden değişmeli veya neden aynı kalmalı."
    )

    proposed_new_outfit: str = Field(
        description=(
            "Kıyafet değişecekse renkleri ve parçaları kesin şekilde tanımla. "
            "Değişmeyecekse SAME."
        )
    )

    accessories: str = Field(
        description="Yalnızca sahnede gerçekten gerekli aksesuarlar."
    )

    emotion: str = Field(
        description="Doğal duygu ve yüz ifadesi."
    )

    pose: str = Field(
        description="Karakterin doğal beden duruşu."
    )

    camera: str = Field(
        description="Kamera kadrajı ve açı."
    )

    background: str = Field(
        description="Sade ve sahneye uygun arka plan."
    )

    continuity: str = Field(
        description="Önceki ve sonraki sahneyle korunması gereken durum."
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
- small simple black dot eyes
- minimal nose and mouth
- flat matte colors
- very subtle simple shading
- low saturation
- beige
- muted brown
- taupe
- gray
- charcoal
- simple clean environments
- uncluttered composition
- consistent line thickness
- consistent character proportions
- horizontal 16:9 YouTube frame


CHARACTER IDENTITY LOCK:

The uploaded reference image defines WHO the recurring protagonist is.

ALWAYS PRESERVE:

- same recognizable face identity
- same head shape
- same facial proportions
- same eye style
- same ear design
- same skin tone
- same approximate age
- same body proportions
- same simplified cartoon construction


REFERENCE IMAGE DOES NOT DEFINE:

- clothing
- profession
- hat
- uniform
- backpack
- accessories
- pose
- emotion
- location


WARDROBE CONTINUITY:

When an ACTIVE OUTFIT LOCK is supplied,
reproduce that clothing consistently.

Do not randomly redesign clothing.
Do not randomly change colors.
Do not substitute garments.

Only use a new outfit when the prompt explicitly provides
a NEW ACTIVE OUTFIT LOCK.


REAL-LIFE BEHAVIOR:

The character must look and behave naturally for the exact situation.

Do not merely place the character in the right location.
His clothing, body state, pose, accessories and expression must make
sense for that exact moment.


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

    return st.session_state.outfit_by_scene.get(
        scene_number - 1,
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
        else "NONE — determine the correct outfit from the current scene."
    )

    director_prompt = f"""
You are the Scene Director for a consistent illustrated YouTube life-story.

You are NOT creating the image.
You are planning ONE realistic still frame.

PREVIOUS NARRATION:
{previous_text if previous_text else "None"}

CURRENT NARRATION:
{current_text}

NEXT NARRATION:
{next_text if next_text else "None"}

CURRENT LOCKED OUTFIT:
{current_outfit_text}


=================================================
CORE RULE
=================================================

The scene must depict how a NORMAL PERSON would naturally look and behave
at this exact moment in real life.

Do not only choose the correct location.
Make clothing, posture, physical state, accessories and expression
match the exact action and time.


=================================================
WARDROBE LOGIC
=================================================

If there is a previous locked outfit:

DEFAULT = KEEP IT EXACTLY THE SAME.

Only change clothes when the story clearly requires a genuine wardrobe transition.

VALID CHANGE EXAMPLES:

- waking up in pajamas then getting dressed
- explicitly changing clothes
- showering and dressing
- changing into a job uniform
- changing into interview clothes
- changing into pajamas before bed
- changing into sports clothes

NOT VALID REASONS:

- entering a bus
- entering an office
- sitting at a desk
- walking outside
- speaking to a boss
- eating lunch
- changing camera angle
- changing emotion

If wardrobe_change_required is FALSE:

proposed_new_outfit MUST be exactly:
SAME


=================================================
REAL-WORLD BEHAVIOR EXAMPLES
=================================================

NARRATION:
"Sabah alarm çaldığında yataktan kalkıyorsun."

CORRECT:

- bedroom
- early morning
- character has just woken up
- pajamas or sleepwear
- barefoot or socks
- sleepy posture
- sitting up, rubbing eyes, stretching, or reaching for alarm
- unmade bed
- alarm clock visible

MUST NOT INCLUDE:

- work shirt
- office shirt
- belt
- work trousers
- formal pants
- shoes
- backpack
- jacket
- hat
- delivery uniform


NARRATION:
"Hızlıca hazırlanıp evden çıkıyorsun."

CORRECT:

- character is now dressed for the day
- leaving through normal residential front door
- ordinary workday clothing
- awake and purposeful
- shoes on

POSSIBLE:

- small everyday backpack only if useful

MUST NOT INCLUDE:

- suitcase
- rolling luggage
- travel bag
- airport context
- moving boxes
- delivery uniform


NARRATION:
"Kalabalık bir otobüste işe doğru yolculuk ediyorsun."

CORRECT:

- crowded urban public bus
- commuting to work
- EXACT SAME workday outfit from previous scene
- natural commuter posture

MUST NOT INCLUDE:

- vacation luggage
- tour bus
- airport shuttle
- new outfit
- delivery uniform


NARRATION:
"Masana geçip bilgisayarını açıyorsun."

CORRECT:

- normal office desk
- office environment
- SAME outfit as commute scene
- character opening or using computer

MUST NOT INCLUDE:

- delivery uniform
- delivery cap
- warehouse
- parcel
- factory


=================================================
SEMANTIC RULES
=================================================

1. Illustrate ONLY the CURRENT sentence.

2. Previous and next sentences are context only.

3. Do not invent another event.

4. Do not exaggerate ordinary actions.

5. Do not interpret leaving home as travel.

6. Do not add luggage unless explicitly required.

7. Never infer profession from the character reference image.

8. Preserve continuity.

9. Be conservative and literal.
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

    return ScenePlan.model_validate_json(
        response.text
    )


# =========================================================
# OUTFIT LOCK
# =========================================================

def resolve_outfit(
    scene_number,
    plan
):

    previous_outfit = get_previous_outfit(
        scene_number
    )

    # İlk sahne: Director belirler
    if not previous_outfit:

        if (
            plan.proposed_new_outfit
            and plan.proposed_new_outfit.upper() != "SAME"
        ):

            active_outfit = plan.proposed_new_outfit

        else:

            # İlk sahnede fallback yok.
            # Director kıyafeti doğru belirlemek zorunda.
            active_outfit = (
                "scene-appropriate clothing determined by the exact narration"
            )

    # Gerçek kıyafet değişimi
    elif (
        plan.wardrobe_change_required
        and plan.proposed_new_outfit.upper() != "SAME"
    ):

        active_outfit = plan.proposed_new_outfit

    # Aynı kıyafet devam
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

    must_include = (
        ", ".join(plan.must_include)
        if plan.must_include
        else "None"
    )

    must_not_include = (
        ", ".join(plan.must_not_include)
        if plan.must_not_include
        else "None"
    )

    return f"""
{style}


SCENE:
{scene_number:03}


NARRATION:
"{narration}"


=================================================
SCENE DIRECTOR PLAN
=================================================

LOCATION:
{plan.location}

TIME:
{plan.time_of_day}

MAIN ACTION:
{plan.main_action}

NATURAL HUMAN BEHAVIOR:
{plan.natural_behavior}

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


=================================================
ACTIVE OUTFIT LOCK
=================================================

{active_outfit}


The ACTIVE OUTFIT LOCK controls the protagonist's clothing.

If this outfit is sleepwear:
keep it as sleepwear.

If this outfit is workday clothing:
keep the same garments and same colors exactly.

Do not substitute garments.
Do not substitute colors.
Do not add a hat unless explicitly included.
Do not add a bag unless scene plan requires one.


=================================================
CHARACTER REFERENCE
=================================================

The uploaded reference image defines:

- character identity
- face
- head shape
- body proportions
- drawing language

It does NOT define:

- current clothing
- current profession
- accessories
- pose
- location


=================================================
MUST INCLUDE
=================================================

{must_include}


=================================================
STRICTLY MUST NOT INCLUDE
=================================================

{must_not_include}


Anything listed above must not appear anywhere in the frame.


=================================================
FINAL IMAGE RULES
=================================================

- exactly ONE still frame
- literal current narration moment
- natural real-life behavior
- correct clothing for this exact moment
- same recurring protagonist identity
- exact ACTIVE OUTFIT LOCK
- no invented event
- no irrelevant objects
- simple 2D cartoon style
- clean composition
- suitable for gentle zoom or pan
- horizontal 16:9
- no text
- no captions
- no subtitles
- no logos
- no watermarks
"""


# =========================================================
# REFERANS PART
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
            "Kıyafet ve davranış sahne mantığıyla yönetilecek."
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
        for value
        in st.session_state.approved.values()
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
            # OUTFIT LOCK
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
                        f"**Zaman:** "
                        f"{plan.time_of_day}"
                    )


                    st.write(
                        f"**Eylem:** "
                        f"{plan.main_action}"
                    )


                    st.write(
                        f"**Doğal davranış:** "
                        f"{plan.natural_behavior}"
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
                        f"**Yeni kıyafet:** "
                        f"{plan.proposed_new_outfit}"
                    )


                    st.write(
                        f"**Duygu:** "
                        f"{plan.emotion}"
                    )


                    st.write(
                        f"**Poz:** "
                        f"{plan.pose}"
                    )


                    st.write(
                        f"**Aksesuar:** "
                        f"{plan.accessories}"
                    )


                    st.write(
                        "**Kesinlikle olmasın:** "
                        + (
                            ", ".join(
                                plan.must_not_include
                            )
                            if plan.must_not_include
                            else "Yok"
                        )
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


                                # PLAN
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


                                # OUTFIT
                                active_outfit = resolve_outfit(
                                    scene_number=index,
                                    plan=plan
                                )


                                # PROMPT
                                image_prompt = build_image_prompt(
                                    channel_name=channel,
                                    scene_number=index,
                                    narration=sentence,
                                    plan=plan,
                                    active_outfit=active_outfit
                                )


                                # IMAGE
                                generated_image = generate_scene_image(
                                    image_prompt=image_prompt,
                                    reference_image=reference_image
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
