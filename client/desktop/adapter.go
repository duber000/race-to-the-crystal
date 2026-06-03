// desktop_adapter.go — ebitengine Game adapter wrapping Kukicha functions
//go:build !js

package main

import (
	"github.com/hajimehoshi/ebiten/v2"
)

// DesktopAdapter implements ebiten.Game by calling Kukicha functions.
type DesktopAdapter struct{}

func (a *DesktopAdapter) Update() error {
	updateFrame()
	return nil
}

func (a *DesktopAdapter) Draw(screen *ebiten.Image) {
	drawFrame(screen)
}

func (a *DesktopAdapter) Layout(outsideWidth, outsideHeight int) (int, int) {
	return layoutScreen(outsideWidth, outsideHeight)
}
