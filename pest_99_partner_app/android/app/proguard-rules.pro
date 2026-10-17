# Do not add "-keep class ** { *; }" or "-dontobfuscate".
# Those rules stop R8 from renaming code and leave Play's obfuscation score near 0%.

# flutter_local_notifications looks up these classes by name.
-keep class com.dexterous.flutterlocalnotifications.** { *; }
