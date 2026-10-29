idf_component_register(SRCS "app_main.cpp" INCLUDE_DIRS "." "../../smoke_test/main"
                       PRIV_REQUIRES esp_timer esp_psram mbedtls)

set(DEER_EVAL_MODEL_FILE "${CMAKE_CURRENT_LIST_DIR}/../../../artifacts/deer.espdl"
    CACHE FILEPATH "Model for dataset evaluation; defaults to retained deer artifact")
option(DEER_EVAL_VERIFY_GOLDEN "Run the selected export's embedded numerical test vectors" OFF)
get_filename_component(model_file "${DEER_EVAL_MODEL_FILE}" ABSOLUTE BASE_DIR "${CMAKE_SOURCE_DIR}")
if(NOT EXISTS "${model_file}")
    message(FATAL_ERROR "Dataset evaluation model does not exist: ${model_file}")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${model_file}")
file(SIZE "${model_file}" model_bytes)
file(SHA256 "${model_file}" model_sha256)
target_compile_definitions(${COMPONENT_LIB} PRIVATE
    DEER_MODEL_BYTES=${model_bytes} DEER_MODEL_SHA256="${model_sha256}")
if(DEER_EVAL_VERIFY_GOLDEN)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE DEER_EVAL_VERIFY_GOLDEN=1)
endif()
idf_component_get_property(espdl_dir espressif__esp-dl COMPONENT_DIR)
set(cmake_dir "${espdl_dir}/fbs_loader/cmake")
include("${cmake_dir}/utilities.cmake")
target_add_aligned_binary_data(${COMPONENT_LIB} "${model_file}" BINARY RENAME_TO "deer.espdl")
