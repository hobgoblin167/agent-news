import unittest
import tkinter as tk
from tkinter import font as tkfont
from gui import NewsAgentGUI


class StreamFormattingTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = NewsAgentGUI(self.root)

    def tearDown(self):
        self.app.close()

    def reset_output(self):
        self.app.output.configure(state='normal')
        self.app.output.delete('1.0', 'end')
        self.app.output.configure(state='disabled')
        self.app.bold_text = False
        self.app.pending_star = ''

    def test_bold_for_every_possible_token_boundary(self):
        source = 'До **важное** после **новость**.'
        expected = 'До важное после новость.'
        for split in range(len(source) + 1):
            with self.subTest(split=split):
                self.reset_output()
                self.app.append_text(source[:split])
                self.app.append_text(source[split:])
                self.app.append_text('', final=True)
                self.assertEqual(self.app.output.get('1.0', 'end-1c'), expected)
                for position in range(len(expected)):
                    tags = self.app.output.tag_names(f'1.{position}')
                    self.assertEqual('bold' in tags, 3 <= position < 9 or 16 <= position < 23)

    def test_bold_has_distinct_rendered_font(self):
        body = self.app.body_font
        bold = tkfont.Font(root=self.root, font=self.app.output.tag_cget('bold', 'font'))
        self.assertEqual(body.actual('weight'), 'normal')
        self.assertEqual(bold.actual('weight'), 'bold')
        self.assertGreater(bold.measure('Важная новость'), body.measure('Важная новость'))
        self.assertGreater(bold.actual('size'), body.actual('size'))

    def test_plain_digest_template_is_formatted_during_streaming(self):
        source = 'ГЛАВНОЕ\n\n1. Новость дня\nКоротко: Обычный текст.\nПочему это важно: Объяснение.\n\nДЕТАЛИ\n- Факт\nМЕНЕЕ ВАЖНОЕ\n'
        for character in source:
            self.app.append_text(character)
        self.app.append_text('', final=True)
        self.assertEqual(self.app.output.get('1.0', 'end-1c'), source)
        for index in ('1.0', '3.3', '4.0', '5.0', '7.0', '9.0'):
            self.assertIn('structure', self.app.output.tag_names(index), index)
        for index in ('4.10', '5.19', '8.2'):
            self.assertNotIn('structure', self.app.output.tag_names(index), index)

    def test_structural_formatting_does_not_override_inline_bold(self):
        self.app.append_text('Коротко: Это **важно**, остальное обычно.')
        self.assertIn('structure', self.app.output.tag_names('1.0'))
        self.assertIn('bold', self.app.output.tag_names('1.14'))
        self.assertNotIn('structure', self.app.output.tag_names('1.14'))
        self.assertNotIn('bold', self.app.output.tag_names('1.25'))


if __name__ == '__main__':
    unittest.main()
