import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, externalizeDepsPlugin } from "electron-vite";

export default defineConfig({
	main: {
		plugins: [externalizeDepsPlugin({ exclude: ["@vikram/contracts"] })],
	},
	preload: {
		plugins: [externalizeDepsPlugin({ exclude: ["@vikram/contracts", "zod"] })],
		build: {
			rollupOptions: {
				output: { format: "cjs", entryFileNames: "index.js" },
			},
		},
	},
	renderer: {
		plugins: [react(), tailwindcss()],
	},
});
