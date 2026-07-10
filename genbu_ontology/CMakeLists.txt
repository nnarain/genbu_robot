cmake_minimum_required(VERSION 3.8)
project(genbu_ontology)

find_package(ament_cmake REQUIRED)
find_package(ament_robot_ontology REQUIRED)

robot_ontology_register_directory(
  DIRECTORY ontology
)


install(
  DIRECTORY
    launch
    ontology
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
