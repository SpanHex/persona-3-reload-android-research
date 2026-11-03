package com.p3r.poc;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.TextView;
import java.io.File;

public class MainActivity extends Activity {

    static {
        System.loadLibrary("p3r_native_harness");
    }

    public native String runAotValidationSuite(String fixturesDir);

    private TextView tvStatus;
    private TextView tvLogs;
    private Button btnRun;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        tvStatus = findViewById(R.id.tvStatus);
        tvLogs = findViewById(R.id.tvLogs);
        btnRun = findViewById(R.id.btnRun);

        btnRun.setOnClickListener(v -> executeValidation());
    }

    private void executeValidation() {
        btnRun.setEnabled(false);
        tvStatus.setText("Status: Executing AOT Validation Suite...");
        tvLogs.setText("Starting native ARM64 test execution through Android Bionic...\n");

        new Thread(() -> {
            // Determine internal/external fixtures path
            File filesDir = getFilesDir();
            String fixturesPath = filesDir.getAbsolutePath();

            long startTime = System.currentTimeMillis();
            final String reportJson = runAotValidationSuite(fixturesPath);
            final long durationMs = System.currentTimeMillis() - startTime;

            mainHandler.post(() -> {
                btnRun.setEnabled(true);
                tvStatus.setText("Status: Completed in " + durationMs + " ms");
                tvLogs.setText(reportJson);
            });
        }).start();
    }
}
