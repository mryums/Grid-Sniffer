#import libraries
import pygame 
import random
import time
import sys  #to exit the game

# Initialize pygame modules
pygame.init()
pygame.mixer.init()

# CONSTANTS 
MINES = -1 
CELL_SIZE = 40 # Size of each cell 
MARGIN = 5 # Margin between cells

# EXCEPTION HANDLING 

emoji_fonts = ["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"]
FONT = None
for font_name in emoji_fonts:
    try:
        FONT = pygame.font.SysFont(font_name, 28) # Try to load the font
        print("emoji font found works")
        break
    except:
        pass # If font loading fails, try the next one
if FONT is None:
    # Fallback to a generic Arial font if no emoji font is found
    FONT = pygame.font.SysFont("Arial", 28)
    print("No suitable emoji font found")

# Load sounds (with fallback if sound files are not found)
try:
    BOMB_SOUND = pygame.mixer.Sound("assets/bomb_sound.wav")
    DIG_SOUND = pygame.mixer.Sound("assets/dig_sound.wav")
except pygame.error:
    BOMB_SOUND = None
    DIG_SOUND = None
    print("Could not load sound files from 'assets/'. Sounds will be disabled.")

# Define colors used in the game
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200) # Color for unrevealed cells
DARK_GRAY = (100, 100, 100)  # Color for cell borders
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
OVERLAY_COLOR = (0, 0, 0, 150) # Semi-transparent black for game over screen overlay

# random Colors for bomb explosions 
BOMB_COLORS = [(255, 192, 203), (221, 160, 221), (144, 238, 144), (255, 255, 224)] # Pink, Plum, Light Green, Light Yellow

# Colors for numbers which tell neighboring bombs
NUMBER_COLORS = {
    1: BLUE,
    2: GREEN,
    3: RED,
    4: (128, 0, 128),  # Purple
    5: (128, 0, 0),    # Maroon
    6: (64, 224, 208), # Turquoise
    7: (0, 0, 0),      # Black
    8: (105, 105, 105),# Dim Gray
}

# Function to load images or use emoji as fallback
def load_img(path, fallback_text):
    """
    Loads an image from the given path and scales it, or creates a surface
    with an emoji if the image fails to load.
    """
    try:
        img = pygame.image.load(path)
        # Scale image to fit within the cell, leaving a small border for aesthetics
        scaled_img = pygame.transform.scale(img, (CELL_SIZE - 6, CELL_SIZE - 6))
        print(f"YES Loaded image from: {path}")
        return scaled_img
    except pygame.error:
        print(f"NO Failed to load image from: {path}, using emoji: {fallback_text}")
        # Create a transparent surface for the emoji, slightly smaller than cell size
        surface = pygame.Surface((CELL_SIZE - 6, CELL_SIZE - 6), pygame.SRCALPHA)
        text = FONT.render(fallback_text, True, BLACK)
        # Center the emoji text on the created surface
        text_rect = text.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
        surface.blit(text, text_rect)
        return surface

# Load game assets (flag and bomb images/emojis)
FLAG_IMAGE = load_img("assets/flag.png", "🚩")
BOMB_IMAGE = load_img("assets/bomb.png", "💣")

# Game class to manage all logic and state
class Grid_snifferGame:
    def __init__(self, size, bombs):
        self.size = size # Size of the square grid (e.g., 9 for 9x9)
        self.bombs = bombs # Number of mines to place
        self.board = self.create_board() # The hidden game board with mines and numbers
        self.visible = [[False for _ in range(size)] for _ in range(size)] # Tracks which cells are revealed
        self.flagged = [[False for _ in range(size)] for _ in range(size)] # Tracks which cells are flagged
        self.dug = set() # Stores coordinates of revealed cells for efficient lookup
        self.game_over = False # True if the game has ended (win or lose)
        self.start_time = time.time() # Time when the game started
        self.victory = False # True if the player won

    def create_board(self):
        """
        Initializes the game board, places mines randomly, and calculates
        neighboring bomb counts for non-mine cells.
        """
        board = [[0 for _ in range(self.size)] for _ in range(self.size)] # Initialize all cells to 0

        # Place bombs randomly
        bombs_planted = 0
        while bombs_planted < self.bombs:
            r, c = random.randint(0, self.size - 1), random.randint(0, self.size - 1)
            if board[r][c] != MINES: # Only place if not already a mine
                board[r][c] = MINES
                bombs_planted += 1
                print(f" AT ROW:{r} COULMN:{c} MINE IS PLACED \n")
        print(bombs_planted)

        # Calculate neighboring bomb counts for all non-mine cells
        for r in range(self.size):
            for c in range(self.size):
                if board[r][c] == MINES:
                    continue # Skip if it's a mine
                board[r][c] = self.count_neighbouring_bombs(r, c, board)
        return board

    def count_neighbouring_bombs(self, r, c, board):
        """
        Counts the number of mines in the 8 surrounding cells of a given cell (r, c).
        """
        count = 0
        size = self.size
        # Iterate through all 8 neighboring cells (including the cell itself, which is skipped)
        for i in [r - 1, r, r + 1]:
            for j in [c - 1, c, c + 1]:
                if i == r and j == c:
                    continue # Skip the its own cell
                # Check if the neighbor is within the board boundaries
                if 0 <= i < size and 0 <= j < size:
                    if board[i][j] == MINES:
                        count += 1
        return count

    def reveal_cell(self, r, c):
        """
        Recursively reveals a cell and its neighbors if it's a '0' (no adjacent mines).
        """
        # Do not reveal if already revealed or flagged
        if (r, c) in self.dug or self.flagged[r][c]:
            return

        self.dug.add((r, c)) # Add cell to dug
        self.visible[r][c] = True # Mark cell as visible

        # If the current cell has 0 neighboring bombs,reveal all its neighbors
        if self.board[r][c] == 0:
            for dr in [-1, 0, 1]: # change in rows
                for dc in [-1, 0, 1]: # change in columns
                    nr = r + dr # Neighbor row
                    nc = c + dc # Neighbor column
                    if (nr, nc) == (r, c):
                        continue # Skip itself
                    # Check if neighbor is within board boundaries
                    if 0 <= nr < self.size and 0 <= nc < self.size:
                        self.reveal_cell(nr, nc) # Recursive call

    def dig(self, r, c):
        """
        Handles a 'dig' action (left-click) on a cell.
        Checks for mines and updates game state.
        """
        if self.visible[r][c] or self.flagged[r][c]:
            return # Do nothing if cell is already visible or flagged

        if self.board[r][c] == MINES:
            if BOMB_SOUND:
                BOMB_SOUND.play() # Play bomb sound if available
            self.game_over = True # Game ends if a mine is dug
            self.victory = False # Player loses
        else:
            if DIG_SOUND:
                DIG_SOUND.play() # Play dig sound if available

        self.reveal_cell(r, c) # Always reveal the cell after digging

    def is_victory(self):
        """
        Checks if the player has won the game.
        Victory condition: all non-mine cells are visible.
        """
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] != MINES and not self.visible[r][c]:
                    return False # Found an unrevealed non-mine cell, so not yet won
        return True # display non-mine cells

    def reveal_all_bombs(self):
        """
        Reveals all bomb locations on the board, called when the game is lost.
        """
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == MINES:
                    self.visible[r][c] = True
                    draw_board(screen, self)
                    pygame.display.update()
                    pygame.time.delay(100)
     
    def toggle_flag(self, r, c):
        """
        Toggles the flag on (right-click).
        Flags can only be placed on unrevealed cells.
        """
        if not self.visible[r][c]: # Only allow flagging on unrevealed cells
            self.flagged[r][c] = not self.flagged[r][c] # Toggle flag state

# UI functions for drawing the game
def draw_board(screen, game):
    """
    Draws the entire game board on the Pygame screen.
    """
    for row in range(game.size):
        for col in range(game.size):
            x = col * (CELL_SIZE + MARGIN) # X-coordinate for the cell's top-left corner
            y = row * (CELL_SIZE + MARGIN) # Y-coordinate for the cell's top-left corner
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE) # Create a rectangle for the cell

            if game.visible[row][col]:
                # Cell is revealed
                if game.board[row][col] == MINES:
                    # It's a mine, draw with a bomb color and image
                    color = random.choice(BOMB_COLORS) # Pick a random bomb color
                    pygame.draw.rect(screen, color, rect)
                    # Center the bomb image within the cell
                    img_rect = BOMB_IMAGE.get_rect(center=rect.center)
                    screen.blit(BOMB_IMAGE, img_rect.topleft)
                else:
                    # It's a number or empty cell, draw white
                    pygame.draw.rect(screen, WHITE, rect)
                    if game.board[row][col] > 0:
                        # Draw the number if it's greater than 0
                        num = game.board[row][col]
                        color = NUMBER_COLORS.get(num, BLACK) # Get color from dictionary, default to black
                        text = FONT.render(str(num), True, color)
                        text_rect = text.get_rect(center=rect.center) # Center the text
                        screen.blit(text, text_rect)
            else:
                # Cell is unrevealed
                pygame.draw.rect(screen, LIGHT_GRAY, rect) # Draw light gray background
                pygame.draw.rect(screen, DARK_GRAY, rect, 2) # Draw dark gray border

                if game.flagged[row][col]:
                    # Draw flag image if cell is flagged
                    img_rect = FLAG_IMAGE.get_rect(center=rect.center) # Center the flag image
                    screen.blit(FLAG_IMAGE, img_rect.topleft) # Blit the flag image directly

def main_menu():
    """
    Displays the main menu allowing the player to choose difficulty.
    """
    global screen, WIDTH, HEIGHT
    WIDTH, HEIGHT = 400, 400 # Fixed window size for the menu
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Grid Sniffer - Select Level")

    # Define difficulty levels: (board_size, number_of_bombs)
    difficulties = {
        "Easy": (9, 10),
        "Medium": (12, 20),
        "Hard": (16, 40)
    }

    menu_font = pygame.font.SysFont("Arial", 36) # Larger font for title
    instruction_font = pygame.font.SysFont("Arial", 28) # Font for difficulty options

    while True:
        screen.fill(WHITE) # Clear screen with white background

        # Draw game title
        title_text = menu_font.render("GRID SNIFFER", True, BLACK)
        title_rect = title_text.get_rect(center=(WIDTH // 2, 50))
        screen.blit(title_text, title_rect)

        y_position_for_text = 150 # Starting Y position for the first option
        option_rects = [] # To store rectangles of clickable options

        # Draw difficulty options
        for i, (name, (board_size, num_bombs)) in enumerate(difficulties.items()):
            text_str = (f"{name}: {board_size}x{board_size} grid, {num_bombs} bombs")
            text = instruction_font.render(text_str, True, BLACK)
            rect = text.get_rect(center=(WIDTH // 2, y_position_for_text))
            screen.blit(text, rect)
            option_rects.append(rect) # Store rect for click detection
            y_position_for_text += 60 # Move down for the next option

        pygame.display.flip() # Update the full display Surface to the screen

        # Event handling for menu
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit() # Exit the game
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos() # Get mouse click position
                for i, rect in enumerate(option_rects):
                    if rect.collidepoint(mx, my): # Check if click is within an option's rectangle
                        chosen_size, chosen_bombs = list(difficulties.values())[i]
                        game_loop(chosen_size, chosen_bombs) # Directly start the game loop
                        return # Exit the main_menu loop as game_loop will handle flow

def display_game_over_screen(screen, game, final_elapsed_time, current_size, current_bombs):
    """
    Displays the game over screen with win/lose message, final time, and restart options.
    """
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR) # Fill with semi-transparent black
    screen.blit(overlay, (0, 0)) # Draw overlay over the current game state

    # Fonts for game over screen
    title_font = pygame.font.SysFont("Arial", 48, bold=True)
    message_font = pygame.font.SysFont("Arial", 36)
    button_font = pygame.font.SysFont("Arial", 30)

    # Determine message and color
    if game.victory:
        message = "YOU WIN!"
        message_color = GREEN
    else:
        game.reveal_all_bombs()
        message = "GAME OVER!"
        message_color = RED

    # Draw title message
    title_text = title_font.render(message, True, message_color)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
    screen.blit(title_text, title_rect)

    # Draw final time
    time_text = message_font.render(f"Time: {final_elapsed_time}s", True, WHITE)
    time_rect = time_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
    screen.blit(time_text, time_rect)

    # Define button properties
    button_width = 200 
    button_height = 50
    button_y_start = HEIGHT // 2 + 30
    button_spacing = 20

    # "Play Again" button
    play_again_rect = pygame.Rect(
        WIDTH // 2 - button_width // 2,
        button_y_start,
        button_width,
        button_height
    )
    # "Main Menu" button
    main_menu_rect = pygame.Rect(
        WIDTH // 2 - button_width // 2,
        button_y_start + button_height + button_spacing,
        button_width,
        button_height
    )

    while True:
        mouse_pos = pygame.mouse.get_pos()
        
        # Draw "Play Again" button
        play_again_color = BLUE if play_again_rect.collidepoint(mouse_pos) else (50, 50, 200) # Darker blue on hover
        pygame.draw.rect(screen, play_again_color, play_again_rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, play_again_rect, 2, border_radius=10) # Border
        play_again_text = button_font.render("Play Again", True, WHITE)
        play_again_text_rect = play_again_text.get_rect(center=play_again_rect.center)
        screen.blit(play_again_text, play_again_text_rect)

        # Draw "Main Menu" button
        main_menu_color = BLUE if main_menu_rect.collidepoint(mouse_pos) else (50, 50, 200) # Darker blue on hover
        pygame.draw.rect(screen, main_menu_color, main_menu_rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, main_menu_rect, 2, border_radius=10) # Border
        main_menu_text = button_font.render("Main Menu", True, WHITE)
        main_menu_text_rect = main_menu_text.get_rect(center=main_menu_rect.center)
        screen.blit(main_menu_text, main_menu_text_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if play_again_rect.collidepoint(mouse_pos):
                    game_loop(current_size, current_bombs) # Restart with same difficulty
                    return # Exit this display_game_over_screen loop
                elif main_menu_rect.collidepoint(mouse_pos):
                    main_menu() # Go back to main menu
                    return # Exit this display_game_over_screen loop

def game_loop(size, bombs):
    """
    Main game loop where the game is played.
    Handles user input, updates game state, and draws the board.
    """
    global screen, WIDTH, HEIGHT
    # Calculate window size based on board size and cell dimensions
    WIDTH = size * (CELL_SIZE + MARGIN) + MARGIN # Add final margin for consistent spacing
    HEIGHT = WIDTH + 50 # Extra space at the bottom for timer/info
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Grid Sniffer") # Set window title
    game = Grid_snifferGame(size, bombs) # Create a new game instance
    clock = pygame.time.Clock() # To control frame rate

    final_elapsed_time = 0 # To store the time when the game ends

    running = True # Flag to control the main game loop
    while running:
        screen.fill(WHITE) # Clear screen with white background
        draw_board(screen, game) # Draw the current state of the game board

        # Display elapsed time
        if not game.game_over:
            elapsed = int(time.time() - game.start_time)
            final_elapsed_time = elapsed # Continuously update final_elapsed_time until game over
        timer_text = FONT.render(f"Time: {final_elapsed_time}s", True, BLACK)
        screen.blit(timer_text, (10, HEIGHT - 40)) # Position timer at bottom-left
      

        # Check for victory condition (only if game is not already over)
        if not game.game_over:
            if game.is_victory():
                game.game_over = True # Set game_over to True
                game.victory = True # Player won

        # If game is over, set running to False to exit the loop
        if game.game_over:
            running = False # Exit the game loop

        # Event handling for game play
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit() # Exit the game
            elif event.type == pygame.MOUSEBUTTONDOWN and not game.game_over:
                # Only process clicks if the game is not over
                x, y = pygame.mouse.get_pos() # Get mouse click position
                # Ensure click is within the game board area (above the timer/info area)
                if y < size * (CELL_SIZE + MARGIN):
                    r, c = y // (CELL_SIZE + MARGIN), x // (CELL_SIZE + MARGIN)
                    # Ensure calculated coordinates are within board bounds
                    if 0 <= r < size and 0 <= c < size:
                        if event.button == 1: # Left click (dig)
                            game.dig(r, c)
                        elif event.button == 3: # Right click (toggle flag)
                            game.toggle_flag(r, c)

        pygame.display.flip() # Update the full display Surface to the screen
        clock.tick(30) # Limit frame rate 

    # After the game loop ends (game_over is True)
    if not game.victory:
        game.reveal_all_bombs() # Reveal all bomb locations when game is lost
        draw_board(screen, game) # Redraw the board to show revealed bombs
        pygame.display.flip() # Update display to show bombs
        pygame.time.delay(1500) # Pause for a moment to let player see the bombs

    # Display the custom game over screen
    display_game_over_screen(screen, game, final_elapsed_time, size, bombs)

def main():
    main_menu() # Start the main menu; which handle starting game_loop or exiting

if __name__ == "__main__":
    main() # Run the main function
