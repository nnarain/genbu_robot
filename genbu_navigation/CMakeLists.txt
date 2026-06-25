cmake_minimum_required(VERSION 3.8)
project(genbu_navigation)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/tf_tree_diagnostics.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
