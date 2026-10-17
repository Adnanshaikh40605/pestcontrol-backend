package com.pestcontrol99.partner

import android.os.Bundle
import androidx.activity.enableEdgeToEdge
import io.flutter.embedding.android.FlutterFragmentActivity

class MainActivity : FlutterFragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // FlutterActivity is not a ComponentActivity, so edge-to-edge has to
        // live on FlutterFragmentActivity. Android 15 already draws this way
        // when the target SDK is 35+; this keeps older phones on the same layout.
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
    }
}
