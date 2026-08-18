import streamlit as st
import re
import io

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from PIL import Image


# =========================================================
# SAYFA AYARLARI
# =========================================================

st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Video Studio")
st.caption("Kontrollü AI video üretim paneli")


# =========================================================
# GEMINI CLIENT
# =========================================================

try:
    client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    client = None


# =========================================================
# KULLANILAN MODELLER
# =========================================================

SCENE_DIRECTOR_MODEL = "gemini-3.1-flash-lite"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"


# =========================================================
# SCENE DIRECTOR ÇIKTI ŞEMASI
# =========================================================

class ScenePlan(BaseModel):

    location: str = Field(
        description="Sahnenin tek ve net mekanı."
    )

    time_of_day: str = Field(
        description="Sabah, gündüz, akşam veya gece."
    )

    main_action: str = Field(
        description="Ana karakterin bu karede yaptığı tek ana eylem."
    )

    wardrobe: str = Field(
        description="Hikayenin mevcut durumuna uygun kıyafet."
    )

    accessories: str = Field(
        description="Yalnızca bu sahnede gerçekten gerekli aksesuarlar. Yoksa none."
    )

    emotion: str = Field(
        description="Karakterin doğal yüz ifadesi ve duygusu."
    )

    pose: str = Field(
        description="Karakterin beden duruşu."
    )

    camera: str = Field(
        description="Kamera kadrajı ve açı."
    )

    background: str = Field(
        description="Sade ve sahneye uygun arka plan."
    )

    continuity: str = Field(
        description="Önceki ve sonraki sahnelerle korunacak görsel süreklilik."
    )

    must_include: list[str] = Field(
        description="Görselde mutlaka bulunması gereken öğeler."
    )

    must_not_include: list[str] = Field(
        description="Görselde kesinlikle bulunmaması gereken öğeler."
    )


# =========================================================
# KANAL GÖRSEL KİMLİĞİ
# =========================================================

CHANNEL_PROFILES = {

    "Başka Bir Hayat": """
STYLE LOCK — BAŞKA BİR HAYAT

Create a clean simple 2D cartoon editorial illustration.

PERMANENT CHANNEL VISUAL STYLE:

- clean 2D cartoon illustration
- bold clean dark outlines
- rounded simplified human anatomy
- rounded heads
- small simple black dot eyes
- minimal nose and mouth
- flat matte colors
- very subtle simple shading
- muted low-saturation palette
- beige
- taupe
- muted brown
- gray
- charcoal
- simple clean environments
- uncluttered composition
- clear visual storytelling
- consistent line thickness
- consistent character proportions
- horizontal 16:9 YouTube composition


MAIN CHARACTER IDENTITY LOCK:

The uploaded reference image defines WHO the recurring main character is.

PRESERVE:

- same recognizable face identity
- same head shape
- same facial proportions
- same eye design
- same ear design
- same skin tone
- same approximate age
- same body proportions
- same simplified cartoon construction
- same overall character identity


IMPORTANT:

The reference image is NOT a wardrobe reference.

The reference image is NOT an occupation reference.

DO NOT permanently copy:

- hat
- cap
- uniform
- shirt
- pants
- shoes
- backpack
- bag
- occupational equipment
- pose
- facial expression
- background
- profession


Wardrobe must be selected from the CURRENT STORY SCENE.

Examples:

Sleeping:
sleepwear or pajamas.

At home:
casual home clothing.

Going to a normal office job:
ordinary clean workday clothing.

Office:
shirt, polo, sweater or other believable office clothing.

Job interview:
neat interview clothing.

Delivery worker:
delivery uniform ONLY if narration says he works as a delivery worker.

Construction:
construction clothing ONLY when narration requires it.


VISUAL CONTINUITY:

Every frame must feel like another shot from the same illustrated series.

STRICTLY AVOID:

- photography
- photorealism
- realistic skin texture
- realistic photography lighting
- 3D rendering
- Pixar
- anime
- manga
- realistic graphic novel art
- painterly art
- glossy advertising look
- vivid saturated colors
- excessive textures
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
- elegant 2D editorial illustration
- warm beige
- soft ivory
- natural pale oak
- muted sage green
- low saturation
- gentle natural morning light
- minimalist Japanese interiors
- calm composition
- one clear scene
- no irrelevant decorative objects
- no vivid colors
- no orange or strong yellow cast
- horizontal 16:9
- no text
- no captions
- no logos
- no watermarks

If a reference image is supplied:
preserve identity while allowing clothing, expression and accessories
to change naturally according to the current narration.
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
}

for key, default_value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# =========================================================
# SCENE DIRECTOR
# =========================================================

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
You are the Scene Director for a narrated 2D YouTube life-story video.

You are NOT generating the image.

Your job is to transform the CURRENT narration sentence into a precise,
literal and visually unambiguous ONE-FRAME scene plan.


PREVIOUS SENTENCE:
{previous_text if previous_text else "None"}


CURRENT SENTENCE:
{current_text}


NEXT SENTENCE:
{next_text if next_text else "None"}


CRITICAL RULES:

1. Illustrate ONLY the CURRENT sentence.

2. Previous and next sentences exist only to understand context and continuity.

3. Do not invent a new event.

4. Do not exaggerate an ordinary event.

5. Never interpret "leaving home" as:
- going on vacation
- traveling
- moving house
- going to airport
- carrying luggage

unless the narration explicitly says so.

6. Never add:
- suitcase
- rolling luggage
- travel bag
- boxes
- package
- delivery equipment
- helmet
- uniform
- hat
- work tools

unless the current story context requires them.

7. Clothing must fit the character's current situation.

8. Never infer the character's occupation from the reference image.

9. Preserve story continuity.


IMPORTANT INTERPRETATION EXAMPLES:


CURRENT:
"Sabah alarm çaldığında yataktan kalkıyorsun."

PLAN:
Bedroom.
Character has just woken up.
Sleepwear.
Tired expression.
Alarm clock visible.

MUST NOT INCLUDE:
work uniform
hat
backpack
luggage


CURRENT:
"Hızlıca hazırlanıp evden çıkıyorsun."

PLAN:
Normal residential home entrance.
Character is leaving home to go to work.
Ordinary workday clothing.
Walking through or just outside front door.

Possible:
small normal everyday backpack.

MUST NOT INCLUDE:
suitcase
rolling luggage
travel bag
airport context
moving boxes
delivery uniform


CURRENT:
"Kalabalık bir otobüste işe doğru yolculuk ediyorsun."

PLAN:
Crowded urban public bus.
Character commuting to work.
Same workday clothing as previous scene.
Standing or sitting among commuters.

MUST NOT INCLUDE:
tour bus
airport shuttle
vacation luggage
delivery uniform


CURRENT:
"Masana geçip bilgisayarını açıyorsun."

PLAN:
Ordinary office desk.
Character is an office employee in this scene.
Office-appropriate clothing.
Character opening or using desktop/laptop computer.

MUST NOT INCLUDE:
delivery uniform
delivery cap
parcel
warehouse
factory


Be conservative.
Be literal.
Do not add objects that are not needed.
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

    plan = ScenePlan.model_validate_json(
        response.text
    )

    return plan


# =========================================================
# GÖRSEL PROMPTU
# =========================================================

def build_image_prompt(
    channel_name,
    scene_number,
    narration,
    plan
):

    style = CHANNEL_PROFILES[channel_name]

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

    prompt = f"""
{style}


SCENE NUMBER:
{scene_number:03}


ORIGINAL NARRATION:
"{narration}"


SCENE DIRECTOR PLAN:


LOCATION:
{plan.location}


TIME OF DAY:
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
{must_include}


STRICTLY MUST NOT INCLUDE:
{must_not_include}


FINAL RULES:

Create exactly ONE still image.

Follow the Scene Director plan literally.

Do not reinterpret the narration.

Do not invent a second event.

Do not add objects because they exist in the reference character image.

The reference image defines:

CHARACTER IDENTITY
+
GENERAL CARTOON DRAWING LANGUAGE

ONLY.

It does NOT define:

WARDROBE
PROFESSION
ACCESSORIES
POSE
LOCATION


Wardrobe must follow SCENE DIRECTOR.

Accessories must follow SCENE DIRECTOR.

If an object is listed under MUST NOT INCLUDE,
it must not appear anywhere in the image.

Keep the protagonist recognizable as the same recurring cartoon character.

Facial expression may change.

Clothing may change.

Accessories may change.

Character identity must not change.

Keep composition suitable for gentle zoom or pan.

Horizontal 16:9.

No text.
No caption.
No subtitle.
No logo.
No watermark.
"""

    return prompt


# =========================================================
# REFERANS GÖRSELİ BYTE'A ÇEVİR
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
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="16:9"
            )
        )
    )

    if not response.candidates:
        raise RuntimeError(
            "Gemini hiçbir aday görsel döndürmedi."
        )

    generated_image = None

    for candidate in response.candidates:

        if candidate.content is None:
            continue

        if not candidate.content.parts:
            continue

        for part in candidate.content.parts:

            if part.inline_data is None:
                continue

            mime_type = (
                part.inline_data.mime_type
                or ""
            )

            if not mime_type.startswith(
                "image/"
            ):
                continue

            generated_image = Image.open(
                io.BytesIO(
                    part.inline_data.data
                )
            ).convert("RGB")

            break

        if generated_image is not None:
            break

    if generated_image is None:
        raise RuntimeError(
            "Gemini yanıtında kullanılabilir görsel bulunamadı."
        )

    return generated_image


# =========================================================
# KANAL SEÇİMİ
# =========================================================

channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen"
    ]
)


# =========================================================
# KARAKTER REFERANSI
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

    col_ref1, col_ref2 = st.columns(
        [
            1,
            3
        ]
    )

    with col_ref1:

        st.image(
            reference_image,
            caption="Referans karakter",
            use_container_width=True
        )

    with col_ref2:

        st.success(
            "Referans yüklendi. "
            "Karakter kimliği korunacak; "
            "kıyafet, aksesuar, meslek görünümü ve ifade "
            "sahneye göre değişecek."
        )


elif channel == "Başka Bir Hayat":

    st.warning(
        "Başka Bir Hayat için referans karakter yüklemeden "
        "seri üretime geçme."
    )


st.divider()


# =========================================================
# VIDEO METNİ
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
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

        st.session_state.sentences = sentences

        st.session_state.images = {}

        st.session_state.approved = {}

        st.session_state.prompts = {}

        st.session_state.scene_plans = {}


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


            # -----------------------------------------
            # SCENE DIRECTOR PLANI
            # -----------------------------------------

            if index in st.session_state.scene_plans:

                plan = (
                    st.session_state.scene_plans[index]
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
                        f"**Ana eylem:** "
                        f"{plan.main_action}"
                    )

                    st.write(
                        f"**Kıyafet:** "
                        f"{plan.wardrobe}"
                    )

                    st.write(
                        f"**Aksesuar:** "
                        f"{plan.accessories}"
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
                        f"**Kamera:** "
                        f"{plan.camera}"
                    )

                    st.write(
                        f"**Arka plan:** "
                        f"{plan.background}"
                    )

                    st.write(
                        f"**Süreklilik:** "
                        f"{plan.continuity}"
                    )

                    st.write(
                        "**Mutlaka olsun:** "
                        + (
                            ", ".join(
                                plan.must_include
                            )
                            if plan.must_include
                            else "Yok"
                        )
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


            # -----------------------------------------
            # ÜRETİLMİŞ GÖRSEL
            # -----------------------------------------

            if index in st.session_state.images:

                st.image(
                    st.session_state.images[index],
                    use_container_width=True
                )


            # -----------------------------------------
            # BUTONLAR
            # -----------------------------------------

            col1, col2 = st.columns(
                2
            )


            with col1:

                button_label = (
                    "🔄 Aynı Planla Yeniden Üret"
                    if index in st.session_state.images
                    else "🎨 Görsel Üret"
                )


                if st.button(
                    button_label,
                    key=f"generate_{index}",
                    use_container_width=True
                ):

                    with st.spinner(
                        f"Sahne {index:03} "
                        f"yorumlanıyor ve hazırlanıyor..."
                    ):

                        try:

                            # ---------------------------------
                            # SAHNE PLANI
                            # ---------------------------------

                            if index in st.session_state.scene_plans:

                                plan = (
                                    st.session_state.scene_plans[
                                        index
                                    ]
                                )

                            else:

                                plan = create_scene_plan(
                                    current_text=sentence,
                                    previous_text=previous_text,
                                    next_text=next_text
                                )

                                st.session_state.scene_plans[
                                    index
                                ] = plan


                            # ---------------------------------
                            # GÖRSEL PROMPT
                            # ---------------------------------

                            image_prompt = build_image_prompt(
                                channel_name=channel,
                                scene_number=index,
                                narration=sentence,
                                plan=plan
                            )


                            # ---------------------------------
                            # GÖRSEL
                            # ---------------------------------

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


            # -----------------------------------------
            # PROMPT
            # -----------------------------------------

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
