import { describe, expect, it } from "vitest";
import { citationSchema, feedbackStatusSchema } from "./index";

describe("API v1 contracts", () => {
	it("requires explicit learning feedback values", () => {
		expect(feedbackStatusSchema.options).toEqual([
			"understood",
			"unclear",
			"review_later",
		]);
		expect(feedbackStatusSchema.safeParse("confused_forever").success).toBe(
			false,
		);
	});

	it("rejects prose-only citations", () => {
		expect(citationSchema.safeParse({ excerpt: "page 1" }).success).toBe(false);
	});
});
