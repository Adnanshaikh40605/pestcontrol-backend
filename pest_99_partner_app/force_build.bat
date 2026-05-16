@echo off
set "JAVA_HOME=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot"
set "GRADLE_JAVA_HOME=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot"
set "PATH=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot\bin;%PATH%"
set "STUDIO_JDK=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot"
set "JDK_HOME=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot"
set "GRADLE_OPTS=-Dorg.gradle.daemon=false -Dorg.gradle.java.home="C:/Program Files/Microsoft/jdk-21.0.8.9-hotspot""
flutter build apk --split-per-abi --release
