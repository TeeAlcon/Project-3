import streamlit as st

CUSTOM_CSS = """
    <style>

    :root {
        --text-color: hsla(210, 50%, 95%, 1);
        --shadow-color: hsla(210, 40%, 52%, .4);
        --btn-color: #0505A9;
    }

    div.stButton > button {

        position: relative;
        overflow: hidden;

        width: 100%;
        padding: 12px 20px;

        border: none;
        border-radius: 8px;

        font-weight: 900;
        text-transform: uppercase;

        color: var(--text-color);
        background-color: var(--btn-color);

        box-shadow: var(--shadow-color) 2px 2px 22px;

        transition:
            transform 0.25s ease,
            box-shadow 0.25s ease,
            background-color 0.25s ease;
    }

    /* Floating bubbles */
    div.stButton > button::before {
        content: "";

        position: absolute;
        top: 0;
        left: 0;

        width: 100%;
        height: 300%;

        opacity: 0.6;
        pointer-events: none;

        background:
            radial-gradient(circle at 20% 35%,
            transparent 0,
            transparent 2px,
            white 3px,
            white 4px,
            transparent 4px),

            radial-gradient(circle at 75% 44%,
            transparent 0,
            transparent 2px,
            white 3px,
            white 4px,
            transparent 4px),

            radial-gradient(circle at 46% 52%,
            transparent 0,
            transparent 4px,
            white 5px,
            white 6px,
            transparent 6px);

        animation: bubbles 5s linear infinite;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 25px rgba(0,120,255,.6);}

    div.stButton > button:active {
        transform: scale(0.98);}

    div.stButton > button:focus {
        outline: none;
        box-shadow: 0 0 30px rgba(0,120,255,.8);}

    @keyframes bubbles {
        from {
        transform: translateY(0);
        }

        to {
        transform: translateY(-66%);
        }
    }

    </style>
    """

def apply_styles():
    st.markdown(
        CUSTOM_CSS,
        unsafe_allow_html=True
    )