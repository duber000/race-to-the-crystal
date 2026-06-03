// desktop_main.go — Entry point for the Race to the Crystal desktop client
//
//go:build !js

package main

import (
	"github.com/hajimehoshi/ebiten/v2"
)

func DesktopMain() {
	ebiten.SetWindowTitle("Race to the Crystal")
	ebiten.SetWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
	ebiten.SetWindowResizingMode(ebiten.WindowResizingModeEnabled)
	err := ebiten.RunGame(&DesktopAdapter{})
	if err != nil {
		panic(err)
	}
}

func main() {
	DesktopMain()
}
