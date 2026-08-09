// Command goconstfix rewrites repeated string literals in Go packages into
// Str* constants (goconst debt paydown bulk slice). Proven: Hivemind ticks
// #199 (pkg/channel 296->0), #200 (pkg/canvas 221->0) — 912 literal rewrites
// in one pass.
//
// Strategy:
//   - collect flagged strings per package from a golangci-lint JSON dump
//   - assign Str* names (dedup vs existing identifiers)
//   - rewrite pass: record ACTUAL usage files per string while rewriting
//     (goconst flags per-file occurrences; a string flagged in tests may also
//     be used in production files with fewer occurrences)
//   - write constants.go (used by any non-test file) and/or constants_test.go
//     (used ONLY by _test.go files) — per directory = per Go package, so
//     subpackage trees get their own constants files automatically
//   - AST-rewrite every matching string literal to the constant ident
//   - skip struct tags, import paths, and const-decl RHS literals
//
// Usage:
//   1. golangci-lint run --default=none -E goconst --uniq-by-line=false \
//        --max-issues-per-linter=0 --max-same-issues=0 \
//        --output.json.path=/tmp/goconst_<pkg>.json ./pkg/<X>/...
//      (JSON contains ALL config-enabled linters — the tool regex-matches
//      only goconst text and prints WARN: unparsed for the rest, harmless)
//   2. go build -o /tmp/goconstfix-bin . && /tmp/goconstfix-bin <dump.json> <repo-root>
//   3. go build ./... && go vet && gofmt -l && go test, re-dump expecting 0
package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode"
)

type Issue struct {
	Text string `json:"Text"`
	Pos  struct {
		Filename string `json:"Filename"`
	} `json:"Pos"`
}

type StringLoc struct {
	Files map[string]bool // file -> used
}

type constEntry struct {
	val  string
	name string
}

var strPat = regexp.MustCompile("string `([^`]*)` has (\\d+) occurrences")

// pkgInfo holds the flagged strings for one package.
type pkgInfo struct {
	dir      string
	name     string
	strings  map[string]*StringLoc // literal value -> locations
	existing map[string]bool       // all identifiers already in package
	names    map[string]string     // literal value -> constant name
	usedName map[string]bool
}

func camel(s string) string {
	var b strings.Builder
	upper := true
	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			if upper {
				b.WriteRune(unicode.ToUpper(r))
				upper = false
			} else {
				b.WriteRune(r)
			}
		} else {
			upper = true
		}
	}
	return b.String()
}

func (p *pkgInfo) constName(val string) string {
	if n, ok := p.names[val]; ok {
		return n
	}
	base := "Str" + camel(val)
	if base == "Str" {
		base = "StrEmpty"
	}
	n := base
	for i := 2; p.existing[n] || p.usedName[n]; i++ {
		n = fmt.Sprintf("%s%d", base, i)
	}
	p.names[val] = n
	p.usedName[n] = true
	return n
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: goconstfix <issues.json> <repo-root>")
		os.Exit(2)
	}
	raw, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	var data struct {
		Issues []Issue `json:"Issues"`
	}
	if err := json.Unmarshal(raw, &data); err != nil {
		panic(err)
	}
	_ = os.Args[2] // repo root; filenames in JSON are already relative

	pkgs := map[string]*pkgInfo{}
	getPkg := func(file string) *pkgInfo {
		dir := filepath.Dir(file)
		if p, ok := pkgs[dir]; ok {
			return p
		}
		p := &pkgInfo{
			dir:      dir,
			strings:  map[string]*StringLoc{},
			existing: map[string]bool{},
			names:    map[string]string{},
			usedName: map[string]bool{},
		}
		pkgs[dir] = p
		return p
	}

	// Collect flagged strings.
	for _, iss := range data.Issues {
		m := strPat.FindStringSubmatch(iss.Text)
		if m == nil {
			fmt.Println("WARN: unparsed:", iss.Text)
			continue
		}
		val := m[1]
		file := iss.Pos.Filename
		p := getPkg(file)
		sl, ok := p.strings[val]
		if !ok {
			sl = &StringLoc{Files: map[string]bool{}}
			p.strings[val] = sl
		}
		sl.Files[file] = true
	}

	// Discover package names + existing identifiers.
	for dir, p := range pkgs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			panic(err)
		}
		for _, e := range entries {
			if e.IsDir() || !strings.HasSuffix(e.Name(), ".go") {
				continue
			}
			fpath := filepath.Join(dir, e.Name())
			fset := token.NewFileSet()
			f, err := parser.ParseFile(fset, fpath, nil, parser.ParseComments)
			if err != nil {
				panic(fmt.Sprintf("parse %s: %v", fpath, err))
			}
			if p.name == "" {
				p.name = f.Name.Name
			}
			ast.Inspect(f, func(n ast.Node) bool {
				if id, ok := n.(*ast.Ident); ok {
					p.existing[id.Name] = true
				}
				return true
			})
		}
	}

	// Assign names (from flagged set; actual usage files filled during rewrite).
	for _, p := range pkgs {
		for val := range p.strings {
			p.constName(val)
		}
	}

	// Rewrite pass: replace literals AND record actual usage files.
	totalRewrites := 0
	for dir, p := range pkgs {
		entries, err := os.ReadDir(dir)
		if err != nil {
			panic(err)
		}
		for _, e := range entries {
			if e.IsDir() || !strings.HasSuffix(e.Name(), ".go") {
				continue
			}
			fpath := filepath.Join(dir, e.Name())
			fset := token.NewFileSet()
			f, err := parser.ParseFile(fset, fpath, nil, parser.ParseComments)
			if err != nil {
				panic(fmt.Sprintf("parse %s: %v", fpath, err))
			}
			changed := false
			constRHS := constRHSSet(f)
			// Custom walk: descend everywhere EXCEPT struct tags (Field.Tag).
			var walk func(n ast.Node) bool
			walk = func(n ast.Node) bool {
				switch t := n.(type) {
				case *ast.Field:
					// visit names/types but NOT the tag (struct tag literal)
					for _, nm := range t.Names {
						if !walk(nm) {
							return false
						}
					}
					if t.Type != nil && !walk(t.Type) {
						return false
					}
					return true
				case *ast.BasicLit:
					if t.Kind != token.STRING {
						return true
					}
					// never rewrite import paths
					if isImportPath(f, t) {
						return true
					}
					val, err := strconv.Unquote(t.Value)
					if err != nil {
						return true
					}
					name, ok := p.names[val]
					if !ok {
						return true
					}
					// skip if this literal is the RHS of its own const decl
					if constRHS[t] {
						return true
					}
					// record actual usage
					if sl, ok := p.strings[val]; ok {
						sl.Files[fpath] = true
					}
					t.Kind = token.IDENT
					t.Value = name
					changed = true
					totalRewrites++
					return true
				}
				// default: descend into children
				for _, c := range children(n) {
					if c != nil && !walk(c) {
						return false
					}
				}
				return true
			}
			walk(f)
			if changed {
				var buf strings.Builder
				if err := format.Node(&buf, fset, f); err != nil {
					panic(fmt.Sprintf("format %s: %v", fpath, err))
				}
				if err := os.WriteFile(fpath, []byte(buf.String()), 0o644); err != nil {
					panic(err)
				}
			}
		}
	}
	fmt.Println("total literal rewrites:", totalRewrites)

	// Classify by ACTUAL usage (post-rewrite) and write constants files.
	for _, p := range pkgs {
		var normal, test []constEntry
		for val, sl := range p.strings {
			testOnly := true
			for f := range sl.Files {
				if !strings.HasSuffix(f, "_test.go") {
					testOnly = false
				}
			}
			e := constEntry{val, p.names[val]}
			if testOnly {
				test = append(test, e)
			} else {
				normal = append(normal, e)
			}
		}
		sort.Slice(normal, func(i, j int) bool { return normal[i].name < normal[j].name })
		sort.Slice(test, func(i, j int) bool { return test[i].name < test[j].name })
		writeConstants(p, normal, test)
	}
}

// constRHSSet returns the set of BasicLit nodes that are RHS values of CONST decls
// (NOT var decls — var RHS literals may still be rewritten safely).
func constRHSSet(f *ast.File) map[*ast.BasicLit]bool {
	set := map[*ast.BasicLit]bool{}
	ast.Inspect(f, func(n ast.Node) bool {
		gd, ok := n.(*ast.GenDecl)
		if !ok || gd.Tok != token.CONST {
			return true
		}
		for _, s := range gd.Specs {
			vs, ok := s.(*ast.ValueSpec)
			if !ok {
				continue
			}
			for _, v := range vs.Values {
				if bl, ok := v.(*ast.BasicLit); ok {
					set[bl] = true
				}
			}
		}
		return true
	})
	return set
}

// isImportPath reports whether lit is a BasicLit in an import spec path position.
func isImportPath(f *ast.File, lit *ast.BasicLit) bool {
	found := false
	ast.Inspect(f, func(n ast.Node) bool {
		if found {
			return false
		}
		is, ok := n.(*ast.ImportSpec)
		if !ok {
			return true
		}
		if is.Path == ast.Node(lit) {
			found = true
			return false
		}
		return true
	})
	return found
}

// children returns the direct AST children of n (reflect-based, like go/ast's walk).
func children(n ast.Node) []ast.Node {
	v := reflect.ValueOf(n)
	if v.Kind() != reflect.Ptr {
		return nil
	}
	v = v.Elem()
	if v.Kind() != reflect.Struct {
		return nil
	}
	var out []ast.Node
	for i := 0; i < v.NumField(); i++ {
		f := v.Field(i)
		switch f.Kind() {
		case reflect.Interface:
			if !f.IsNil() {
				if c, ok := f.Interface().(ast.Node); ok {
					out = append(out, c)
				}
			}
		case reflect.Slice:
			for j := 0; j < f.Len(); j++ {
				if c, ok := f.Index(j).Interface().(ast.Node); ok {
					out = append(out, c)
				}
			}
		case reflect.Ptr:
			if !f.IsNil() {
				if c, ok := f.Interface().(ast.Node); ok {
					out = append(out, c)
				}
			}
		}
	}
	return out
}

func writeConstants(p *pkgInfo, normal, test []constEntry) {
	writeOne := func(path, pkgName string, entries []constEntry) {
		if len(entries) == 0 {
			return
		}
		var b strings.Builder
		fmt.Fprintf(&b, "// Package %s string constants — shared literals (goconst debt paydown).\npackage %s\n\nconst (\n", pkgName, pkgName)
		for _, e := range entries {
			fmt.Fprintf(&b, "\t// %s is the string literal %q.\n\t%s = %q\n", e.name, e.val, e.name, e.val)
		}
		b.WriteString(")\n")
		if err := os.WriteFile(path, []byte(b.String()), 0o644); err != nil {
			panic(err)
		}
		fmt.Println("wrote", path, "( ", len(entries), "consts )")
	}
	writeOne(filepath.Join(p.dir, "constants.go"), p.name, normal)
	writeOne(filepath.Join(p.dir, "constants_test.go"), p.name, test)
}
