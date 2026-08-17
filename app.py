import streamlit as st
import re

st.set_page_config(
    page_title="AI Video Studio",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 AI Video Studio")
st.caption("Kontrollü AI video üretim paneli")

channel = st.selectbox(
    "Kanal",
    [
        "Başka Bir Hayat",
        "Sessiz Düzen"
    ]
)

st.divider()

st.subheader("1. Video Metni")

script = st.text_area(
    "Video metnini buraya yapıştır",
    height=350,
    placeholder="Hazırladığımız video metnini buraya yapıştır..."
)

if st.button("Metni Cümlelere Ayır", type="primary"):

    if not script.strip():
        st.warning("Önce video metnini gir.")
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

if "sentences" in st.session_state:

    sentences = st.session_state["sentences"]

    st.success(
        f"Metin hazır: {len(sentences)} anlatım parçası bulundu."
    )

    st.subheader("2. Sahne Listesi")

    for index, sentence in enumerate(sentences[:20], start=1):

        with st.container(border=True):

            st.markdown(f"### Sahne {index:03}")
            st.write(sentence)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.button(
                    "🎨 Görsel Üret",
                    key=f"generate_{index}"
                )

            with col2:
                st.button(
                    "✏️ Prompt",
                    key=f"prompt_{index}"
                )

            with col3:
                st.button(
                    "✓ Onayla",
                    key=f"approve_{index}"
                )

    if len(sentences) > 20:
        st.info(
            f"İlk 20 sahne gösteriliyor. Toplam {len(sentences)} sahne var."
        )
