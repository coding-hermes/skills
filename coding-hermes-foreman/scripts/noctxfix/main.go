// Command noctxfix rewrites http.NewRequest / httptest.NewRequest / exec.Command
// calls into their *WithContext variants. Companion to goconstfix for the
// co-located noctx fold-in required after every goconst slice (CI only-new-issues
// flags pre-existing noctx on rewriter-touched lines).
//
// Proven: hivemind tick 216 (internal/controller) — 717 rewrites across the package
// after the goconst slice, zero CI lint regressions.
//
// Correct behavior:
//   - http.NewRequest(m, u, b)  -> http.NewRequestWithContext(context.Background(), m, u, b)
//   - httptest.NewRequest(m,u,b)-> httptest.NewRequestWithContext(context.Background(), m, u, b)
//   - exec.Command(a...)        -> exec.CommandContext(context.Background(), a...)
//   - rewrites ALL occurrences in the package (full-file uniform conversion kills
//     future only-new-issues noise on the same files — tick 207 pattern)
//
// CRITICAL PITFALL (tick 216): appending to f.Imports does NOT render — format.Node
// writes from f.Decls. The ImportSpec MUST be inserted into the import GenDecl's
// Specs (or a new GenDecl prepended to f.Decls), then ast.SortImports.
//
// Usage:
//   1. go build -o /tmp/noctxfix-bin .
//   2. /tmp/noctxfix-bin <package-dir>     # e.g. internal/controller
//   3. gofmt -w <package-dir> && go build ./... && go vet ./<pkg>/...
package main

import (
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: noctxfix <package-dir>")
		os.Exit(2)
	}
	dir := os.Args[1]
	entries, err := os.ReadDir(dir)
	if err != nil {
		panic(err)
	}
	total := 0
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
		needsCtx := false
		ast.Inspect(f, func(n ast.Node) bool {
			ce, ok := n.(*ast.CallExpr)
			if !ok {
				return true
			}
			sel, ok := ce.Fun.(*ast.SelectorExpr)
			if !ok {
				return true
			}
			x, ok := sel.X.(*ast.Ident)
			if !ok {
				return true
			}
			var newSel string
			switch {
			case x.Name == "httptest" && sel.Sel.Name == "NewRequest":
				newSel = "NewRequestWithContext"
			case x.Name == "http" && sel.Sel.Name == "NewRequest":
				newSel = "NewRequestWithContext"
			case x.Name == "exec" && sel.Sel.Name == "Command":
				newSel = "CommandContext"
			default:
				return true
			}
			ctx := &ast.CallExpr{
				Fun: &ast.SelectorExpr{
					X:   ast.NewIdent("context"),
					Sel: ast.NewIdent("Background"),
				},
			}
			ce.Args = append([]ast.Expr{ctx}, ce.Args...)
			sel.Sel.Name = newSel
			needsCtx = true
			changed = true
			total++
			return true
		})
		if !changed {
			continue
		}
		// Insert "context" into the import GenDecl — NOT f.Imports (doesn't render).
		if needsCtx && !hasImport(f, "context") {
			var impDecl *ast.GenDecl
			for _, d := range f.Decls {
				if gd, ok := d.(*ast.GenDecl); ok && gd.Tok == token.IMPORT {
					impDecl = gd
					break
				}
			}
			spec := &ast.ImportSpec{
				Path: &ast.BasicLit{Kind: token.STRING, Value: `"context"`},
			}
			if impDecl == nil {
				impDecl = &ast.GenDecl{Tok: token.IMPORT, Lparen: 1}
				impDecl.Specs = append(impDecl.Specs, spec)
				f.Decls = append([]ast.Decl{impDecl}, f.Decls...)
			} else {
				impDecl.Specs = append(impDecl.Specs, spec)
			}
			ast.SortImports(fset, f)
		}
		var buf strings.Builder
		if err := format.Node(&buf, fset, f); err != nil {
			panic(fmt.Sprintf("format %s: %v", fpath, err))
		}
		if err := os.WriteFile(fpath, []byte(buf.String()), 0o644); err != nil {
			panic(err)
		}
	}
	fmt.Println("total noctx rewrites:", total)
}

func hasImport(f *ast.File, path string) bool {
	for _, im := range f.Imports {
		if im.Path != nil && strings.Trim(im.Path.Value, `"`) == path {
			return true
		}
	}
	return false
}
