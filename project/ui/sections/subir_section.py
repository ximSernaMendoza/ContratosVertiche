from __future__ import annotations

import streamlit as st

from config.settings import SETTINGS


class SubirSection:
    def __init__(self, storage) -> None:
        self.storage = storage

    def render(self) -> None:
        if not st.session_state.get("is_admin"):
            st.error("No tienes los permisos para subir documentos.")
            st.stop()

        st.subheader("Subir documentos a la base de datos")
        st.caption(f"Bucket: {SETTINGS.BUCKET_NAME}")

        target_folder = st.text_input("Carpeta destino (opcional)", value="")
        uploaded_files = st.file_uploader(
            "Selecciona uno o varios archivos (PDF recomendado)",
            type=None,
            accept_multiple_files=True
        )

        colu1, colu2 = st.columns(2)
        with colu1:
            overwrite = st.checkbox("Sobrescribir si ya existe", value=False)
        with colu2:
            clear_cache = st.checkbox("Limpiar caché del índice al subir", value=True)

        if st.button("Subir al bucket", disabled=not uploaded_files):
            ok = 0
            fail = 0

            existing_names = set(self.storage.list_root_files())
            for uf in uploaded_files:
                try:
                    fname = self.storage.safe_filename(uf.name)
                    dest = f"{target_folder.strip().strip('/')}/{fname}".strip("/") if target_folder else fname

                    if not overwrite and fname in existing_names:
                        st.warning(f"Ya existe y no se sobrescribió: {dest}")
                        fail += 1
                        continue


                    file_bytes = uf.getvalue()
                    content_type = uf.type or "application/octet-stream"
                    self.storage.upload(file_bytes, dest, content_type=content_type)
                    st.success(f"Subido: {dest} ({len(file_bytes):,} bytes)")
                    ok += 1
                except Exception as e:
                    st.error(f"Error subiendo {uf.name}: {e}")
                    fail += 1

            st.info(f"Resultado: {ok} subidos, {fail} con error")

            if clear_cache:
                st.cache_resource.clear()
                st.success("Caché limpiada. En la siguiente consulta se reindexará.")

        st.divider()
        st.subheader("Archivos en el bucket")

        names = self.storage.list_root_files()

        if names:
            with st.expander(f"📂 Contratos ({len(names)})", expanded=False):
                st.markdown("\n".join([f"- {n}" for n in sorted(names)]))
        else:
                st.write("No hay archivos en la raíz del bucket.")
