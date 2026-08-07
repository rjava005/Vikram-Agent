import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [react()],
	test: {
		environment: "jsdom",
		env: {
			VIKRAM_API_TOKEN: "test-local-capability-token-000000000000000000",
			VIKRAM_API_BASE_URL: "http://127.0.0.1:8742",
		},
		clearMocks: true,
		restoreMocks: true,
		include: ["src/**/*.test.ts", "tests/**/*.test.ts", "tests/**/*.test.tsx"],
		exclude: ["tests/smoke/**"],
	},
});
