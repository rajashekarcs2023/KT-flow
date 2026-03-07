import { GoogleGenAI } from "@google/genai";

export const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });
export const MODEL = "gemini-3.1-pro-preview";
