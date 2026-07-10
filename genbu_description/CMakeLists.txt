cmake_minimum_required(VERSION 3.20)
project(genbu_description)

find_package(ament_cmake REQUIRED)

option(GENBU_ENABLE_HCDF "Enable HCDF-based URDF generation for genbu_description" OFF)

if(GENBU_ENABLE_HCDF)
  find_package(genbu_hcdf REQUIRED)
  find_package(hcdf_robot_generator REQUIRED)

  get_filename_component(genbu_hcdf_prefix "${genbu_hcdf_DIR}/../../.." ABSOLUTE)

  set(GENBU_HCDF_INPUT_FILE "${genbu_hcdf_prefix}/share/genbu_hcdf/hcdf/robot.hcdf")
  set(GENBU_HCDF_OUTPUT_FILE "${CMAKE_CURRENT_BINARY_DIR}/generated/robot.hcdf.urdf")

  hcdf_generate_urdf(
    ALL
    TARGET genbu_generate_hcdf_urdf
    HCDF_FILE "${GENBU_HCDF_INPUT_FILE}"
    OUTPUT_FILE "${GENBU_HCDF_OUTPUT_FILE}"
    INSTALL_DESTINATION "share/${PROJECT_NAME}/urdf"
  )
endif()

install(
  DIRECTORY
    launch
    urdf
    meshes
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
