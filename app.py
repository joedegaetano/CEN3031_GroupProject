import streamlit as st


def build_demo_items() -> list[str]:
    return [
        "Python virtual environment",
        "Streamlit app shell",
        "Reusable smoke test",
    ]


def main() -> None:
    st.set_page_config(page_title="CEN3031 Streamlit Starter", layout="centered")

    st.title("CEN3031 Group Project")
    st.subheader("Python + Streamlit environment is ready")

    st.write(
        "This starter app gives you a clean base to build your Streamlit project."
    )

    st.markdown("### Included in this starter")
    for item in build_demo_items():
        st.write(f"- {item}")

    st.markdown("### Next steps")
    st.code("streamlit run app.py", language="bash")


if __name__ == "__main__":
    main()
