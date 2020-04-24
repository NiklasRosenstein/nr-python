# nr.markdown

Extends the [misaka][] Markdown library for a couple of extensions.

* `inside-html`: Support Markdown inside HTML tags. Requires the `bs4` package
* `smartypants`: Automatically apply `misaka.smartypants()` on the input
  Markdown. Enabled by default
* `pygments`: Highlight code blocks with Pygments. Requires the `pygments` package
* `url-transform`: Transform links and image URLs with a callback function.
  Enabled by default, but only actually does something if the
  `url_transform_callback` option is set
* `toc`: Generates a table of contents while rendering, but does not actually
  render a TOC into the output. The generated TOC data structure can be
  accessed via the `Markdown.toc` attribute. Enabled by default

[misaka]: https://github.com/FSX/misaka

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
