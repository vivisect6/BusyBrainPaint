"""BusyBrainPaint - Paint-by-numbers mandala game."""

from pathlib import Path

import pygame

from puzzle_loader import load_puzzle


def main() -> None:
    """Main entry point."""
    pygame.init()

    # Load stub puzzle
    puzzle_dir = Path(__file__).parent / "puzzles" / "stub"

    if not puzzle_dir.exists():
        print(f"Puzzle not found at {puzzle_dir}")
        print("Run 'python create_stub_puzzle.py' first to generate test assets.")
        return

    print("Loading puzzle...")
    puzzle = load_puzzle(puzzle_dir)

    print(f"Puzzle loaded successfully!")
    print(f"  Dimensions: {puzzle.width}x{puzzle.height}")
    print(f"  Regions: {puzzle.num_regions}")
    print(f"  Palette colors: {len(puzzle.palette)}")

    # Print some stats
    print("\nRegion stats (first 5):")
    for i in range(min(5, puzzle.num_regions)):
        area = puzzle.region_area[i]
        centroid = puzzle.region_centroid[i]
        bbox = puzzle.region_bbox[i]
        neighbors = len(puzzle.adj[i])
        color_idx = puzzle.region_color[i]
        print(
            f"  Region {i}: area={area}, centroid=({centroid[0]:.1f}, {centroid[1]:.1f}), "
            f"bbox={bbox}, neighbors={neighbors}, palette_idx={color_idx}"
        )

    # Quick pygame window test
    screen = pygame.display.set_mode((puzzle.width * 4, puzzle.height * 4), pygame.FULLSCREEN)
    pygame.display.set_caption("BusyBrainPaint - Loader Test")

    # Create a surface showing regions colored by their target color
    preview = pygame.Surface((puzzle.width, puzzle.height))
    for region_id in range(puzzle.num_regions):
        color_idx = puzzle.region_color[region_id]
        color = puzzle.palette[color_idx]
        for y, x_start, x_end in puzzle.region_runs[region_id]:
            pygame.draw.line(preview, color, (x_start, y), (x_end - 1, y))

    # Scale up for visibility
    scaled = pygame.transform.scale(preview, (puzzle.width * 4, puzzle.height * 4))

    running = True
    clock = pygame.time.Clock()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                # Any button to exit for now
                if event.button == 1:  # B button typically
                    running = False

        screen.fill((40, 40, 40))
        # Center the preview
        screen_w, screen_h = screen.get_size()
        x = (screen_w - scaled.get_width()) // 2
        y = (screen_h - scaled.get_height()) // 2
        screen.blit(scaled, (x, y))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    print("\nLoader test complete.")


if __name__ == "__main__":
    main()
