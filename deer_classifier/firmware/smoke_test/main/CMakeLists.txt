idf_component_register(SRCS "app_main.cpp" INCLUDE_DIRS "."
                       PRIV_REQUIRES esp_timer esp_psram driver)

set(model_file "${CMAKE_CURRENT_LIST_DIR}/../../../artifacts/deer.espdl")
if(NOT EXISTS "${model_file}")
    message(FATAL_ERROR "Missing deer_classifier/artifacts/deer.espdl")
endif()
file(SIZE "${model_file}" model_bytes)
file(SHA256 "${model_file}" model_sha256)
target_compile_definitions(${COMPONENT_LIB} PRIVATE
    DEER_MODEL_BYTES=${model_bytes} DEER_MODEL_SHA256="${model_sha256}")

# ESP-DL requires aligned model data; normal EMBED_FILES does not promise it.
idf_component_get_property(espdl_dir espressif__esp-dl COMPONENT_DIR)
set(cmake_dir "${espdl_dir}/fbs_loader/cmake")
include("${cmake_dir}/utilities.cmake")
target_add_aligned_binary_data(${COMPONENT_LIB} "${model_file}" BINARY)
