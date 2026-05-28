// Hand-written test helper: a recording stand-in for testing.TB.
// testing.TB has unexported methods, so implementing it from outside the
// testing package requires embedding. Kukicha's type syntax doesn't express
// qualified embedded fields, so this helper lives in Go. It is exported
// under the name FakeTB so the .kuki test file can construct it.

package test_test

import (
	"fmt"
	"testing"
)

type FakeTB struct {
	testing.TB
	Errs []string
}

func (f *FakeTB) Helper() {}

func (f *FakeTB) Errorf(format string, args ...any) {
	f.Errs = append(f.Errs, fmt.Sprintf(format, args...))
}
