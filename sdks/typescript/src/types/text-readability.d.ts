declare module 'text-readability' {
  interface TextReadability {
    fleschKincaidGrade(text: string): number;
    [fn: string]: (text: string) => number;
  }

  const textReadability: TextReadability;
  export default textReadability;
}
