cmake_minimum_required(VERSION 3.20)
project(genbu_hcdf)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    hcdf
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
